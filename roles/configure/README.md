# configure

Configure warpgate via API (roles, users, targets, groups)

## Table of contents

- [Requirements](#requirements)
- [Default Variables](#default-variables)
  - [warpgate_admin_password](#warpgate_admin_password)
  - [warpgate_admin_roles](#warpgate_admin_roles)
  - [warpgate_admin_username](#warpgate_admin_username)
  - [warpgate_api_host](#warpgate_api_host)
  - [warpgate_api_insecure](#warpgate_api_insecure)
  - [warpgate_api_token](#warpgate_api_token)
  - [warpgate_parameters](#warpgate_parameters)
  - [warpgate_roles](#warpgate_roles)
  - [warpgate_target_groups](#warpgate_target_groups)
  - [warpgate_targets](#warpgate_targets)
  - [warpgate_users](#warpgate_users)
- [Dependencies](#dependencies)
- [License](#license)
- [Author](#author)

---

## Requirements

- Minimum Ansible version: `2.1`

## Default Variables

### warpgate_admin_password

Warpgate admin password

**_Type:_** string<br />

### warpgate_admin_roles

Warpgate admin roles (v0.23+). Permissions default to false when omitted.

**_Type:_** list<br />

#### Default value

```YAML
warpgate_admin_roles: []
```

#### Example usage

```YAML

```

### warpgate_admin_username

Warpgate admin username (for automatic API token via POST session)

**_Type:_** string<br />

#### Default value

```YAML
warpgate_admin_username: admin
```

### warpgate_api_host

Warpgate API host

**_Type:_** string<br />

#### Example usage

```YAML
warpgate_api_host: "https://localhost:8888/@warpgate/admin/api/"
```

### warpgate_api_insecure

Warpgate API insecure

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_api_insecure: false
```

### warpgate_api_token

Warpgate API token. If unset, the role will try to obtain one via user API
(POST /auth/login then POST /profile/api-tokens). You can also set it manually (Admin UI).

**_Type:_** string<br />

### warpgate_parameters

Warpgate global parameters (v0.24+). Only the keys you set are changed;
the other parameters keep their current server-side value.
See the warpgate_parameters module documentation for the full key list.

**_Type:_** dict<br />

#### Default value

```YAML
warpgate_parameters: {}
```

#### Example usage

```YAML

```

### warpgate_roles

Warpgate roles. Optional per-role field (v0.24+): is_default
(auto-assign the role to newly created users).

**_Type:_** list<br />

#### Default value

```YAML
warpgate_roles: []
```

#### Example usage

```YAML

```

### warpgate_target_groups

Warpgate target groups

**_Type:_** list<br />

#### Default value

```YAML
warpgate_target_groups: []
```

#### Example usage

```YAML

```

### warpgate_targets

Warpgate targets. Optional v0.23+ fields: rate_limit_bytes_per_second,
default_database_name / idle_timeout on mysql_options / postgres_options,
iam_role on mysql/postgres options (mutually exclusive with password).
Optional v0.25+ fields: jump_host / iam_role on ssh_options,
iam_role on kubernetes_options, protocol_version on postgres_options.

**_Type:_** list<br />

#### Default value

```YAML
warpgate_targets: []
```

#### Example usage

```YAML

```

### warpgate_users

Warpgate users. Optional per-user fields (v0.23+):
rate_limit_bytes_per_second, allowed_ip_ranges, admin_roles.

**_Type:_** list<br />

#### Default value

```YAML
warpgate_users: []
```

#### Example usage

```YAML

```

## Dependencies

None.

## License

MPL2

## Author

Clément Hubert
