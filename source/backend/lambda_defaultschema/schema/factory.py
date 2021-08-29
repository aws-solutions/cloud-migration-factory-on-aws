schema = [
    {
        "schema_name": {
            "S": "wave"
        },

        "attributes": {
            "L": [
                {
                    "M": {
                        "description": {
                            "S": "wave name"
                        },
                        "name": {
                            "S": "wave_name"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "wave status"
                        },
                        "name": {
                            "S": "wave_status"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "wave start time"
                        },
                        "name": {
                            "S": "wave_start_time"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "wave end time"
                        },
                        "name": {
                            "S": "wave_end_time"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                }

            ]
        }
    },

    {
        "schema_name": {
            "S": "app"
        },

        "attributes": {
            "L": [
                {
                    "M": {
                        "description": {
                            "S": "app name"
                        },
                        "name": {
                            "S": "app_name"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "wave id"
                        },
                        "name": {
                            "S": "wave_id"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "cloudendure project name"
                        },
                        "listvalue": {
                            "S": "project1,project2"
                        },
                        "name": {
                            "S": "cloudendure_projectname"
                        },
                        "type": {
                            "S": "list"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "AWS AccountId"
                        },
                        "listvalue": {
                            "S": "111122223333,222233334444"
                        },
                        "name": {
                            "S": "aws_accountid"
                        },
                        "type": {
                            "S": "list"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "AWS Region"
                        },
                        "name": {
                            "S": "aws_region"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                }

            ]
        }
    },

    {
        "schema_name": {
            "S": "server"
        },

        "attributes": {
            "L": [
                {
                    "M": {
                        "description": {
                            "S": "app id"
                        },
                        "name": {
                            "S": "app_id"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "server name"
                        },
                        "name": {
                            "S": "server_name"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "server os family"
                        },
                        "listvalue": {
                            "S": "windows,linux"
                        },
                        "name": {
                            "S": "server_os_family"
                        },
                        "type": {
                            "S": "list"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "Server OS Version"
                        },
                        "name": {
                            "S": "server_os_version"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "server FQDN"
                        },
                        "name": {
                            "S": "server_fqdn"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "server tier"
                        },
                        "name": {
                            "S": "server_tier"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "server environment"
                        },
                        "name": {
                            "S": "server_environment"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "subnet IDs"
                        },
                        "name": {
                            "S": "subnet_IDs"
                        },
                        "type": {
                            "S": "multivalue-string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "securitygroup IDs"
                        },
                        "name": {
                            "S": "securitygroup_IDs"
                        },
                        "type": {
                            "S": "multivalue-string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "subnet IDs test"
                        },
                        "name": {
                            "S": "subnet_IDs_test"
                        },
                        "type": {
                            "S": "multivalue-string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "securitygroup IDs test"
                        },
                        "name": {
                            "S": "securitygroup_IDs_test"
                        },
                        "type": {
                            "S": "multivalue-string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "instance Type"
                        },
                        "name": {
                            "S": "instanceType"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "IAM role"
                        },
                        "name": {
                            "S": "iamRole"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "Private IP"
                        },
                        "name": {
                            "S": "private_ip"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "tags"
                        },
                        "name": {
                            "S": "tags"
                        },
                        "type": {
                            "S": "tag"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "tenancy"
                        },
                        "listvalue": {
                            "S": "Shared,Dedicated,Dedicated host"
                        },
                        "name": {
                            "S": "tenancy"
                        },
                        "type": {
                            "S": "list"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "migration status"
                        },
                        "name": {
                            "S": "migration_status"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                },
                {
                    "M": {
                        "description": {
                            "S": "replication status"
                        },
                        "name": {
                            "S": "replication_status"
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                }
            ]
        }
    }
]
