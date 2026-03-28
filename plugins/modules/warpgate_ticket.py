#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: warpgate_ticket

short_description: Manages Warpgate access tickets

description:
    - This module allows to create and delete temporary access tickets.
    - "B(Note): Tickets are inherently non-idempotent. Each call with
      state=present creates a new ticket with a unique secret. Tickets
      cannot be updated. Use state=absent with a ticket ID to delete."

version_added: "1.0.0"

options:
    host:
        description:
            - Base URL of the Warpgate instance (e.g., https://warpgate.example.com)
        type: str
        required: true
    token:
        description:
            - Warpgate API authentication token. If provided, takes priority over api_username/api_password.
        type: str
        required: false
    api_username:
        description:
            - Warpgate admin username. Use with api_password to obtain a token automatically.
        type: str
        required: false
    api_password:
        description:
            - Warpgate admin password. Use with api_username instead of token.
        type: str
        required: false
    id:
        description:
            - Ticket ID (for deletion)
        type: str
        required: false
    username:
        description:
            - Username for the ticket
        type: str
        required: false
    target_name:
        description:
            - Target name for the ticket
        type: str
        required: false
    expiry:
        description:
            - Ticket expiration date (ISO 8601 format)
        type: str
        required: false
    number_of_uses:
        description:
            - Number of allowed uses
        type: int
        required: false
        default: 0
    description:
        description:
            - Ticket description
        type: str
        required: false
    state:
        description:
            - Desired state of the ticket
        type: str
        choices: ["present", "absent"]
        default: "present"
    insecure:
        description:
            - Disables SSL certificate verification
        type: bool
        default: false
    timeout:
        description:
            - Request timeout in seconds
        type: int
        default: 30

author:
    - Clément Hubert (@plopoyop)
"""

EXAMPLES = """
- name: Create an access ticket
  plopoyop.warpgate.warpgate_ticket:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    username: "admin"
    target_name: "internal-web-app"
    state: present
  register: ticket_result

- name: Display the ticket secret
  ansible.builtin.debug:
    msg: "Ticket secret: {{ ticket_result.secret }}"
  when: ticket_result.secret is defined

- name: Delete a ticket
  plopoyop.warpgate.warpgate_ticket:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    id: "ticket-uuid"
    state: absent
"""

RETURN = """
id:
    description: Ticket ID
    type: str
    returned: when created
secret:
    description: Ticket secret (only available at creation)
    type: str
    returned: when created
    no_log: true
username:
    description: Ticket username
    type: str
    returned: when available
target:
    description: Target name
    type: str
    returned: when available
expiry:
    description: Expiration date
    type: str
    returned: when available
uses_left:
    description: Number of uses remaining
    type: str
    returned: when available
description:
    description: Ticket description
    type: str
    returned: when available
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateClient,
    WarpgateClientError,
    WarpgateAPIError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.ticket import (
    create_ticket,
    delete_ticket,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        id=dict(type="str", required=False),
        username=dict(type="str", required=False),
        target_name=dict(type="str", required=False),
        expiry=dict(type="str", required=False),
        number_of_uses=dict(type="int", required=False, default=0),
        description=dict(type="str", required=False),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[("state", "absent", ["id"])],
    )

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )
    ticket_id = module.params["id"]
    username = module.params["username"]
    target_name = module.params["target_name"]
    expiry = module.params["expiry"]
    number_of_uses = module.params["number_of_uses"]
    description = module.params["description"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {"changed": False, "id": None, "secret": None}

    try:
        client = WarpgateClient(
            host,
            token=token,
            username=api_username,
            password=api_password,
            timeout=timeout,
            insecure=insecure,
        )

        if state == "absent":
            if not module.check_mode:
                delete_ticket(client, ticket_id)
            result["changed"] = True
            result["id"] = ticket_id
            result["diff"] = {
                "before": {"id": ticket_id},
                "after": {},
            }
        else:
            # Tickets are inherently non-idempotent: each creation produces
            # a unique secret. The caller is responsible for gating creation
            # (e.g., with a when: condition or run_once).
            if not module.check_mode:
                ticket_and_secret = create_ticket(
                    client,
                    username=username or "",
                    target_name=target_name or "",
                    expiry=expiry or "",
                    number_of_uses=number_of_uses,
                    description=description or "",
                )

                result["id"] = ticket_and_secret.ticket.id
                result["secret"] = ticket_and_secret.secret
                result["username"] = ticket_and_secret.ticket.username
                result["target"] = ticket_and_secret.ticket.target
                result["expiry"] = ticket_and_secret.ticket.expiry
                result["uses_left"] = ticket_and_secret.ticket.uses_left
                result["description"] = ticket_and_secret.ticket.description
            else:
                result["id"] = "new-ticket-id"

            result["changed"] = True
            result["diff"] = {
                "before": {},
                "after": {
                    "username": username,
                    "target": target_name,
                    "expiry": expiry,
                },
            }

        module.exit_json(**result)

    except WarpgateAPIError as e:
        module.fail_json(
            msg=f"Warpgate API error: {e.message}", status_code=e.status_code
        )
    except WarpgateClientError as e:
        module.fail_json(msg=f"Warpgate client error: {str(e)}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
