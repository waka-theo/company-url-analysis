Enrich email

# Enrich email

# OpenAPI definition

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "zeliq-api",
    "version": "1.0"
  },
  "servers": [
    {
      "url": "https://api.zeliq.com/api"
    }
  ],
  "components": {
    "securitySchemes": {
      "sec0": {
        "type": "apiKey",
        "in": "header",
        "name": "x-api-key"
      }
    }
  },
  "security": [
    {
      "sec0": []
    }
  ],
  "paths": {
    "/contact/enrich/email": {
      "post": {
        "summary": "Enrich email",
        "description": "",
        "operationId": "enrich-email",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "first_name": {
                    "type": "string",
                    "x-readme-id": "0.0"
                  },
                  "last_name": {
                    "type": "string",
                    "x-readme-id": "0.1"
                  },
                  "company": {
                    "type": "string",
                    "description": "Company name or company domain",
                    "x-readme-id": "0.2"
                  },
                  "linkedin_url": {
                    "type": "string",
                    "x-readme-id": "0.3"
                  },
                  "callback_url": {
                    "type": "string",
                    "description": "System will send the enrichment result via an HTTP POST request to the specified URL. \nThis allows you to receive the response asynchronously. Once processing is complete, a POST webhook is triggered with a JSON payload containing the enriched data. The payload structure mirrors the standard API response. Retry Strategy Up to 8 retry attempts are made using exponential backoff, starting at 30 seconds and increasing up to just over 1 hour. https://your-server.com/webhooks/zeliq-callback/3f9e7b2c-91fa-4c34-9b12-bd5e93f45a6c. You can use a Webhook simulator like webhook.site if you don't have your own server.\nNote: Both callback_url and callbackUrl are accepted and behave identically",
                    "x-readme-id": "0.4"
                  }
                },
                "required": [
                  "callback_url"
                ]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "200",
            "content": {
              "application/json": {
                "examples": {
                  "Result": {
                    "value": "{\n    \"credit_used\": \"2\",\n    \"contact\": {\n        \"first_name\": \"first_name\",\n        \"last_name\": \"last_name\",\n        \"domain\": \"domain.com\",\n        \"linkedin_url\": \"https://www.linkedin.com/in/profile_url\",\n        \"most_probable_email\": \"email@zeliq.com\",\n        \"most_probable_email_status\": \"safe to send\",\n        \"emails\": [\n            {\n                \"email\": \"email@zeliq.com\",\n                \"status\": \"safe to send\"\n            }\n        ]\n    }\n}"
                  }
                },
                "schema": {
                  "type": "object",
                  "properties": {
                    "credit_used": {
                      "type": "string",
                      "example": "2"
                    },
                    "contact": {
                      "type": "object",
                      "properties": {
                        "first_name": {
                          "type": "string",
                          "example": "first_name"
                        },
                        "last_name": {
                          "type": "string",
                          "example": "last_name"
                        },
                        "domain": {
                          "type": "string",
                          "example": "domain.com"
                        },
                        "linkedin_url": {
                          "type": "string",
                          "example": "https://www.linkedin.com/in/profile_url"
                        },
                        "most_probable_email": {
                          "type": "string",
                          "example": "email@zeliq.com"
                        },
                        "most_probable_email_status": {
                          "type": "string",
                          "example": "safe to send"
                        },
                        "emails": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "email": {
                                "type": "string",
                                "example": "email@zeliq.com"
                              },
                              "status": {
                                "type": "string",
                                "example": "safe to send"
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          },
          "400": {
            "description": "400",
            "content": {
              "application/json": {
                "examples": {
                  "Result": {
                    "value": "{\n    \"message\": \"property test should not exist\",\n    \"error\": \"VALIDATION_FAILED\",\n    \"statusCode\": 400\n}"
                  }
                },
                "schema": {
                  "type": "object",
                  "properties": {
                    "message": {
                      "type": "string",
                      "example": "property test should not exist"
                    },
                    "error": {
                      "type": "string",
                      "example": "VALIDATION_FAILED"
                    },
                    "statusCode": {
                      "type": "integer",
                      "example": 400,
                      "default": 0
                    }
                  }
                }
              }
            }
          },
          "401": {
            "description": "401",
            "content": {
              "application/json": {
                "examples": {
                  "Result": {
                    "value": "{\n    \"message\": \"Invalid API key\",\n    \"error\": \"Unauthorized\",\n    \"statusCode\": 401\n}"
                  }
                },
                "schema": {
                  "type": "object",
                  "properties": {
                    "message": {
                      "type": "string",
                      "example": "Invalid API key"
                    },
                    "error": {
                      "type": "string",
                      "example": "Unauthorized"
                    },
                    "statusCode": {
                      "type": "integer",
                      "example": 401,
                      "default": 0
                    }
                  }
                }
              }
            }
          }
        },
        "deprecated": false
      }
    }
  },
  "x-readme": {
    "headers": [],
    "explorer-enabled": true,
    "proxy-enabled": true
  },
  "x-readme-fauxas": true
}
```