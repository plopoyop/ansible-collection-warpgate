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
module: warpgate_public_key_credential

short_description: Manages SSH public key credentials for Warpgate users

description:
    - This module allows to add, modify and delete SSH public key credentials.

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
            - Credential ID (for update/delete operations)
        type: str
        required: false
    label:
        description:
            - Label for the public key
        type: str
        required: true
    public_key:
        description:
            - OpenSSH public key
        type: str
        required: true
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
- name: Add an SSH public key to a user
  plopoyop.warpgate.warpgate_public_key_credential:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    label: "Work Laptop"
    public_key: "ssh-rsa AAAAB3NzaC1yc2E... email@example.com"
    state: present

- name: Update a public key
  plopoyop.warpgate.warpgate_public_key_credential:
    host: "https://warpgate.example.com"
    token: "{{ warpgate_api_token }}"
    user_id: "user-uuid"
    credential_id: "credential-uuid"
    label: "Updated Label"
    public_key: "ssh-rsa AAAAB3NzaC1yc2E... email@example.com"
    state: present

- name: Delete a public key
  plopoyop.warpgate.warpgate_public_key_credential:
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
    returned: when created or updated
credential_id:
    description: Credential ID
    type: str
    returned: when created or updated
label:
    description: Public key label
    type: str
    returned: when available
date_added:
    description: Key addition date
    type: str
    returned: when available
last_used:
    description: Last used date
    type: str
    returned: when available
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client import (
    WarpgateClient,
    WarpgateClientError,
    WarpgateAPIError,
)
from ansible_collections.plopoyop.warpgate.plugins.module_utils.warpgate_client.credential import (
    add_public_key_credential,
    get_public_key_credentials,
    update_public_key_credential,
    delete_public_key_credential,
)


def main():
    module_args = dict(
        host=dict(type="str", required=True),
        token=dict(type="str", required=False, no_log=True),
        api_username=dict(type="str", required=False),
        api_password=dict(type="str", required=False, no_log=True),
        user_id=dict(type="str", required=True),
        credential_id=dict(type="str", required=False),
        label=dict(type="str", required=True),
        public_key=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        insecure=dict(type="bool", default=False),
        timeout=dict(type="int", default=30),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[("state", "absent", ["credential_id"])],
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
    label = module.params["label"]
    public_key = module.params["public_key"]
    state = module.params["state"]
    insecure = module.params["insecure"]
    timeout = module.params["timeout"]

    result = {"changed": False, "id": None, "credential_id": None, "label": label}

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
            if not credential_id:
                module.fail_json(msg="credential_id is required when state=absent")

            if not module.check_mode:
                delete_public_key_credential(client, user_id, credential_id)
            result["changed"] = True
            result["id"] = f"{user_id}:{credential_id}"
            result["credential_id"] = credential_id
            result["diff"] = {
                "before": {"label": label, "credential_id": credential_id},
                "after": {},
            }
        else:
            if credential_id:
                # Update an existing credential
                # Retrieve all credentials to find the one to update
                creds = get_public_key_credentials(client, user_id)
                existing_cred = None
                for cred in creds:
                    if cred.id == credential_id:
                        existing_cred = cred
                        break

                if not existing_cred:
                    module.fail_json(
                        msg=f"Credential with ID {credential_id} not found"
                    )

                # Check if modifications are needed
                needs_update = False
                if existing_cred.label != label:
                    needs_update = True
                if existing_cred.openssh_public_key != public_key:
                    needs_update = True

                if needs_update:
                    result["diff"] = {
                        "before": {
                            "label": existing_cred.label,
                            "public_key": existing_cred.openssh_public_key,
                        },
                        "after": {"label": label, "public_key": public_key},
                    }
                    if not module.check_mode:
                        updated_cred = update_public_key_credential(
                            client, user_id, credential_id, label, public_key
                        )
                        result["credential_id"] = updated_cred.id
                        result["label"] = updated_cred.label
                        result["date_added"] = updated_cred.date_added
                        result["last_used"] = updated_cred.last_used
                    result["changed"] = True
                else:
                    result["credential_id"] = existing_cred.id
                    result["label"] = existing_cred.label
                    result["date_added"] = existing_cred.date_added
                    result["last_used"] = existing_cred.last_used

                result["id"] = f"{user_id}:{result['credential_id']}"
            else:
                # Create a new credential
                if not module.check_mode:
                    cred = add_public_key_credential(client, user_id, label, public_key)
                    credential_id = cred.id
                    result["credential_id"] = credential_id
                    result["label"] = cred.label
                    result["date_added"] = cred.date_added
                    result["last_used"] = cred.last_used
                else:
                    result["credential_id"] = "new-credential-id"

                result["id"] = f"{user_id}:{result['credential_id']}"
                result["changed"] = True
                result["diff"] = {
                    "before": {},
                    "after": {"label": label, "public_key": public_key},
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
