# configure

Configure warpgate via API (roles, users, targets, groups)

## Table of contents

- [Requirements](#requirements)
- [Default Variables](#default-variables)
  - [warpgate_admin_password](#warpgate_admin_password)
  - [warpgate_admin_username](#warpgate_admin_username)
  - [warpgate_api_host](#warpgate_api_host)
  - [warpgate_api_insecure](#warpgate_api_insecure)
  - [warpgate_api_token](#warpgate_api_token)
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

### warpgate_roles

Warpgate roles

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

Warpgate targets

**_Type:_** list<br />

#### Default value

```YAML
warpgate_targets: []
```

#### Example usage

```YAML

```

### warpgate_users

Warpgate users

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
