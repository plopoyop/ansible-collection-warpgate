# install

Install warpgate

## Table of contents

- [Requirements](#requirements)
- [Default Variables](#default-variables)
  - [warpgate_admin_password](#warpgate_admin_password)
  - [warpgate_config_file_directory](#warpgate_config_file_directory)
  - [warpgate_config_file_path](#warpgate_config_file_path)
  - [warpgate_data_path](#warpgate_data_path)
  - [warpgate_database_url](#warpgate_database_url)
  - [warpgate_download_url](#warpgate_download_url)
  - [warpgate_executable_path](#warpgate_executable_path)
  - [warpgate_external_host](#warpgate_external_host)
  - [warpgate_http_port](#warpgate_http_port)
  - [warpgate_install_path](#warpgate_install_path)
  - [warpgate_kubernetes_enabled](#warpgate_kubernetes_enabled)
  - [warpgate_kubernetes_port](#warpgate_kubernetes_port)
  - [warpgate_minimize_password_login](#warpgate_minimize_password_login)
  - [warpgate_mysql_enabled](#warpgate_mysql_enabled)
  - [warpgate_mysql_port](#warpgate_mysql_port)
  - [warpgate_postgres_enabled](#warpgate_postgres_enabled)
  - [warpgate_postgres_port](#warpgate_postgres_port)
  - [warpgate_record_sessions](#warpgate_record_sessions)
  - [warpgate_service_enabled](#warpgate_service_enabled)
  - [warpgate_service_file_path](#warpgate_service_file_path)
  - [warpgate_service_name](#warpgate_service_name)
  - [warpgate_service_state](#warpgate_service_state)
  - [warpgate_ssh_enabled](#warpgate_ssh_enabled)
  - [warpgate_ssh_port](#warpgate_ssh_port)
  - [warpgate_sso_providers](#warpgate_sso_providers)
  - [warpgate_system_group](#warpgate_system_group)
  - [warpgate_system_user](#warpgate_system_user)
  - [warpgate_version](#warpgate_version)
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

### warpgate_config_file_directory

#### Default value

```YAML
warpgate_config_file_directory: /etc/warpgate
```

### warpgate_config_file_path

Warpgate config path

**_Type:_** string<br />

#### Default value

```YAML
warpgate_config_file_path: '{{ warpgate_config_file_directory }}/warpgate.yaml'
```

### warpgate_data_path

Warpgate data path

**_Type:_** string<br />

#### Default value

```YAML
warpgate_data_path: /var/lib/warpgate
```

### warpgate_database_url

Warpgate database URL

**_Type:_** string<br />

#### Default value

```YAML
warpgate_database_url: sqlite:{{ warpgate_data_path }}/warpgate.db
```

### warpgate_download_url

#### Default value

```YAML
warpgate_download_url:
  https://github.com/warp-tech/warpgate/releases/download/v{{ warpgate_version
  }}/warpgate-v{{ warpgate_version }}-x86_64-linux
```

### warpgate_executable_path

#### Default value

```YAML
warpgate_executable_path: '{{ warpgate_install_path }}/warpgate'
```

### warpgate_external_host

Warpgate external host

**_Type:_** string<br />

#### Default value

```YAML
warpgate_external_host: localhost
```

### warpgate_http_port

Warpgate HTTP port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_http_port: 8888
```

### warpgate_install_path

#### Default value

```YAML
warpgate_install_path: /usr/bin
```

### warpgate_kubernetes_enabled

Warpgate Kubernetes enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_kubernetes_enabled: false
```

### warpgate_kubernetes_port

Warpgate Kubernetes port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_kubernetes_port: 8443
```

### warpgate_minimize_password_login

When true, the password login form is collapsed behind a toggle on the login page.
Useful for SSO-first environments where password login is only used by admins.

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_minimize_password_login: false
```

### warpgate_mysql_enabled

Warpgate MySQL enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_mysql_enabled: false
```

### warpgate_mysql_port

Warpgate MySQL port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_mysql_port: 33306
```

### warpgate_postgres_enabled

Warpgate PostgreSQL enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_postgres_enabled: false
```

### warpgate_postgres_port

Warpgate PostgreSQL port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_postgres_port: 55432
```

### warpgate_record_sessions

Warpgate record sessions

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_record_sessions: true
```

### warpgate_service_enabled

Enable warpgate service

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_service_enabled: true
```

### warpgate_service_file_path

#### Default value

```YAML
warpgate_service_file_path: /etc/systemd/system/{{ warpgate_service_name
  }}.service
```

### warpgate_service_name

#### Default value

```YAML
warpgate_service_name: warpgate
```

### warpgate_service_state

warpgate service desired state

**_Type:_** string<br />

#### Default value

```YAML
warpgate_service_state: started
```

### warpgate_ssh_enabled

Warpgate SSH enabled

**_Type:_** boolean<br />

#### Default value

```YAML
warpgate_ssh_enabled: false
```

### warpgate_ssh_port

Warpgate SSH port

**_Type:_** int<br />

#### Default value

```YAML
warpgate_ssh_port: 2222
```

### warpgate_sso_providers

Warpgate SSO providers

**_Type:_** list<br />

#### Default value

```YAML
warpgate_sso_providers: []
```

### warpgate_system_group

System group name to create

**_Type:_** string<br />

#### Default value

```YAML
warpgate_system_group: warpgate
```

### warpgate_system_user

System user name to create

**_Type:_** string<br />

#### Default value

```YAML
warpgate_system_user: warpgate
```

### warpgate_version

warpgate version to install

**_Type:_** string<br />

#### Default value

```YAML
warpgate_version: 0.21.1
```

## Dependencies

None.

## License

MPL2

## Author

Clément Hubert
