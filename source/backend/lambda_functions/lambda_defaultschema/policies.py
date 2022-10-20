schema = [
    {
        "policy_id": {
            "S": "1"
        },
        "entity_access": {
            "L": [
                {
                    "M": {
                        "create": {
                            "BOOL": True
                        },
                        "update": {
                            "BOOL": True
                        },
                        "attributes": {
                            "L": [
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "application"
                                        },
                                        "attr_name": {
                                            "S": "app_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "application"
                                        },
                                        "attr_name": {
                                            "S": "app_name"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "application"
                                        },
                                        "attr_name": {
                                            "S": "wave_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "application"
                                        },
                                        "attr_name": {
                                            "S": "cloudendure_projectname"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "application"
                                        },
                                        "attr_name": {
                                            "S": "aws_accountid"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "application"
                                        },
                                        "attr_name": {
                                            "S": "aws_region"
                                        }
                                    }
                                }
                            ]
                        },
                        "schema_name": {
                            "S": "application"
                        },
                        "read": {
                            "BOOL": True
                        },
                        "delete": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "create": {
                            "BOOL": True
                        },
                        "update": {
                            "BOOL": True
                        },
                        "attributes": {
                            "L": [
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "wave"
                                        },
                                        "attr_name": {
                                            "S": "wave_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "wave"
                                        },
                                        "attr_name": {
                                            "S": "wave_name"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "wave"
                                        },
                                        "attr_name": {
                                            "S": "wave_status"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "wave"
                                        },
                                        "attr_name": {
                                            "S": "wave_start_time"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "wave"
                                        },
                                        "attr_name": {
                                            "S": "wave_end_time"
                                        }
                                    }
                                }
                            ]
                        },
                        "schema_name": {
                            "S": "wave"
                        },
                        "read": {
                            "BOOL": True
                        },
                        "delete": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "create": {
                            "BOOL": True
                        },
                        "update": {
                            "BOOL": True
                        },
                        "attributes": {
                            "L": [
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "server_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "app_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "server_name"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "server_os_family"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "server_os_version"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "server_fqdn"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "server_tier"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "server_environment"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "subnet_IDs"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "securitygroup_IDs"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "subnet_IDs_test"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "securitygroup_IDs_test"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "instanceType"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "iamRole"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "private_ip"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "tags"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "tenancy"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "migration_status"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "replication_status"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "r_type"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "network_interface_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "network_interface_id_test"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "server"
                                        },
                                        "attr_name": {
                                            "S": "dedicated_host_id"
                                        }
                                    }
                                }
                            ]
                        },
                        "schema_name": {
                            "S": "server"
                        },
                        "read": {
                            "BOOL": True
                        },
                        "delete": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "create": {
                            "BOOL": True
                        },
                        "update": {
                            "BOOL": True
                        },
                        "attributes": {
                            "L": [
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "database"
                                        },
                                        "attr_name": {
                                            "S": "database_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "database"
                                        },
                                        "attr_name": {
                                            "S": "app_id"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "database"
                                        },
                                        "attr_name": {
                                            "S": "database_name"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "database"
                                        },
                                        "attr_name": {
                                            "S": "database_type"
                                        }
                                    }
                                }
                            ]
                        },
                        "schema_name": {
                            "S": "database"
                        },
                        "read": {
                            "BOOL": True
                        },
                        "delete": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "create": {
                            "BOOL": True
                        },
                        "schema_name": {
                            "S": "mgn"
                        }
                    }
                },
                {
                    "M": {
                        "create": {
                            "BOOL": True
                        },
                        "schema_name": {
                            "S": "ce"
                        }
                    }
                },
                {
                    "M": {
                        "create": {
                            "BOOL": True
                        },
                        "schema_name": {
                            "S": "ssm_job"
                        }
                    }
                },
                {
                    "M": {
                        "create": {
                          "BOOL": True
                        },
                        "update": {
                          "BOOL": True
                        },
                        "attributes": {
                            "L": [
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "script"
                                        },
                                        "attr_name": {
                                            "S": "script_name"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "script"
                                        },
                                        "attr_name": {
                                            "S": "script_description"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "script"
                                        },
                                        "attr_name": {
                                            "S": "fileName"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "script"
                                        },
                                        "attr_name": {
                                            "S": "path"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "script"
                                        },
                                        "attr_name": {
                                            "S": "script_masterfile"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "script"
                                        },
                                        "attr_name": {
                                            "S": "default"
                                        }
                                    }
                                },
                                {
                                    "M": {
                                        "attr_type": {
                                            "S": "script"
                                        },
                                        "attr_name": {
                                            "S": "latest"
                                        }
                                    }
                                }
                            ]
                        },
                        "schema_name": {
                          "S": "script"
                        }
                    }
                }
            ]
        },
        "policy_name": {
            "S": "Administrator"
        }
    },
    {
        "policy_id": {
            "S": "2"
        },
        "policy_name": {
            "S": "ReadOnly"
        },
        "entity_access": {
            "L": [
                {
                    "M": {
                        "schema_name": {
                            "S": "application"
                        },
                        "create": {
                            "BOOL": False
                        },
                        "read": {
                            "BOOL": True
                        },
                        "update": {
                            "BOOL": False
                        },
                        "delete": {
                            "BOOL": False
                        }
                    }
                },
                {
                    "M": {
                        "schema_name": {
                            "S": "wave"
                        },
                        "create": {
                            "BOOL": False
                        },
                        "read": {
                            "BOOL": True
                        },
                        "update": {
                            "BOOL": False
                        },
                        "delete": {
                            "BOOL": False
                        }
                    }
                },
                {
                    "M": {
                        "schema_name": {
                            "S": "server"
                        },
                        "create": {
                            "BOOL": False
                        },
                        "read": {
                            "BOOL": True
                        },
                        "update": {
                            "BOOL": False
                        },
                        "delete": {
                            "BOOL": False
                        }
                    }
                }
            ]
        }
    }
]
