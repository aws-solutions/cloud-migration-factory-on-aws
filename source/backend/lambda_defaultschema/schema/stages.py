schema = [
    {
        "attributes": {
            "L": [
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_name"
                        },
                        "attr_type": {
                            "S": "wave"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_status"
                        },
                        "attr_type": {
                            "S": "wave"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_start_time"
                        },
                        "attr_type": {
                            "S": "wave"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_end_time"
                        },
                        "attr_type": {
                            "S": "wave"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "app_name"
                        },
                        "attr_type": {
                            "S": "app"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_id"
                        },
                        "attr_type": {
                            "S": "app"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "cloudendure_projectname"
                        },
                        "attr_type": {
                            "S": "app"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "aws_accountid"
                        },
                        "attr_type": {
                            "S": "app"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "aws_region"
                        },
                        "attr_type": {
                            "S": "app"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "app_id"
                        },
                        "attr_type": {
                            "S": "server"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "server_fqdn"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "server_os_family"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "server_os_version"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "server_tier"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "server_environment"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "instanceType"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "iamRole"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "private_ip"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "tenancy"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "subnet_IDs_test"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "securitygroup_IDs_test"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "subnet_IDs"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "securitygroup_IDs"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "tags"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                }
            ]
        },
        "stage_id": {
            "S": "1"
        },
        "stage_name": {
            "S": "Pre-migration"
        }
    },
    {
        "attributes": {
            "L": [
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_id"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "cloudendure_projectname"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "aws_accountid"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "migration_status"
                        },
                        "attr_type": {
                            "S": "server"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "replication_status"
                        },
                        "attr_type": {
                            "S": "server"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                }
            ]
        },
        "stage_id": {
            "S": "2"
        },
        "stage_name": {
            "S": "Build"
        }
    },
    {
        "attributes": {
            "L": [
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_id"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "cloudendure_projectname"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "aws_accountid"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "migration_status"
                        },
                        "attr_type": {
                            "S": "server"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "replication_status"
                        },
                        "attr_type": {
                            "S": "server"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                }
            ]
        },
        "stage_id": {
            "S": "3"
        },
        "stage_name": {
            "S": "Validate"
        }
    },
    {
        "attributes": {
            "L": [
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_id"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "cloudendure_projectname"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "aws_accountid"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "replication_status"
                        },
                        "attr_type": {
                            "S": "server"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "migration_status"
                        },
                        "attr_type": {
                            "S": "server"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                }
            ]
        },
        "stage_id": {
            "S": "4"
        },
        "stage_name": {
            "S": "Boot up testing"
        }
    },
    {
        "attributes": {
            "L": [
                {
                    "M": {
                        "attr_name": {
                            "S": "wave_id"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "cloudendure_projectname"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "aws_accountid"
                        },
                        "attr_type": {
                            "S": "app"
                        },
                        "read_only": {
                            "BOOL": True
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "migration_status"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                },
                {
                    "M": {
                        "attr_name": {
                            "S": "replication_status"
                        },
                        "attr_type": {
                            "S": "server"
                        }
                    }
                }
            ]
        },
        "stage_id": {
            "S": "5"
        },
        "stage_name": {
            "S": "Cutover"
        }
    }
]
