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
module: warpgate_password_credential

short_description: Manages password credentials for Warpgate users

description:
    - This module allows to add and delete password credentials.
    - "B(Idempotence): Since the Warpgate API does not return password values,
      idempotence behavior depends on C(update_password).
      With C(on_create) (default), state=present is a no-op when the user
      already has at least one password credential.
      With C(always), existing credentials are deleted and re-created on
      every run."

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
    user_id:
        description:
            - User ID
        type: str
        required: true
    credential_id:
        description:
            - Credential ID (for deletion)
        type: str
        required: false
    password:
        description:
            - Password value.
            - Required when C(state=present).
        type: str
        required: false
        no_log: true
    update_password:
        description:
            - C(on_create) will only set the password if the user has no existing password credential (default).
            - C(always) will delete existing password credentials and re-create with the provided password.
        type: str
        choices: ['on_create', 'always']
        default: on_create
    state:
        description:
            - Desired state of the credential
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
- name: Add a password to a user
  plopoyop.warpgate.warpgate_password_credential:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    password: "{{ user_password }}"
    state: present

- name: Delete a password
  plopoyop.warpgate.warpgate_password_credential:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    credential_id: "credential-uuid"
    state: absent
"""

RETURN = """
id:
    description: Credential ID (format user_id:credential_id)
    type: str
    returned: when created
credential_id:
    description: Credential ID
    type: str
    returned: when created
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateClient,
    WarpgateClientError,
    WarpgateAPIError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.credential import (
    add_password_credential,
    get_password_credentials,
    delete_password_credential,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        user_id=dict(type="str", required=True),
        credential_id=dict(type="str", required=False),
        password=dict(type="str", required=False, no_log=True),
        update_password=dict(
            type="str",
            default="on_create",
            choices=["on_create", "always"],
            no_log=False,
        ),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["password"]),
            ("state", "absent", ["credential_id"]),
        ],
    )

    host = module.params["host"]
    token = (module.params.get("token") or "").strip() or None
    api_username = module.params.get("api_username") or None
    api_password = module.params.get("api_password") or None

    if not token and not (api_username and api_password):
        module.fail_json(
            msg="Provide either token or both api_username and api_password"
        )
    user_id = module.params["user_id"]
    credential_id = module.params["credential_id"]
    password = module.params["password"]
    update_password = module.params["update_password"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {"changed": False, "id": None, "credential_id": None}

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
                delete_password_credential(client, user_id, credential_id)
            result["changed"] = True
            result["id"] = f"{user_id}:{credential_id}"
            result["credential_id"] = credential_id
            result["diff"] = {
                "before": {"user_id": user_id, "credential_id": credential_id},
                "after": {},
            }
        else:
            existing_creds = get_password_credentials(client, user_id)

            if update_password == "on_create" and existing_creds:
                # Already has at least one password credential — no-op
                first = existing_creds[0]
                result["id"] = f"{user_id}:{first.id}"
                result["credential_id"] = first.id
            else:
                # on_create with no creds, or always: (re)create
                existing_count = len(existing_creds)
                if not module.check_mode:
                    # Delete existing credentials when update_password=always
                    if update_password == "always" and existing_creds:
                        for cred in existing_creds:
                            if cred.id:
                                delete_password_credential(client, user_id, cred.id)

                    cred = add_password_credential(client, user_id, password)
                    result["id"] = f"{user_id}:{cred.id}"
                    result["credential_id"] = cred.id
                else:
                    result["id"] = f"{user_id}:new-credential-id"
                    result["credential_id"] = "new-credential-id"
                result["changed"] = True
                result["diff"] = {
                    "before": {
                        "user_id": user_id,
                        "password_credentials_count": existing_count,
                    },
                    "after": {"user_id": user_id, "password_credentials_count": 1},
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
