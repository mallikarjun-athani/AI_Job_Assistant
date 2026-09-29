ANALYSIS_JSON_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': [
        'personal_info', 'summary', 'skills', 'education', 'experience',
        'projects', 'certifications', 'languages', 'keywords', 'target_roles',
    ],
    'properties': {
        'personal_info': {
            'type': 'object',
            'additionalProperties': False,
            'required': ['name', 'email', 'phone', 'location', 'linkedin', 'github', 'portfolio'],
            'properties': {
                field: {'type': ['string', 'null']}
                for field in ('name', 'email', 'phone', 'location', 'linkedin', 'github', 'portfolio')
            },
        },
        'summary': {'type': ['string', 'null']},
        'skills': {'type': 'array', 'items': {'type': 'string'}},
        'education': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['degree', 'institution', 'location', 'start_date', 'end_date', 'grade'],
                'properties': {
                    field: {'type': ['string', 'null']}
                    for field in ('degree', 'institution', 'location', 'start_date', 'end_date', 'grade')
                },
            },
        },
        'experience': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': [
                    'job_title', 'company', 'location', 'start_date', 'end_date', 'description', 'skills',
                ],
                'properties': {
                    'job_title': {'type': ['string', 'null']},
                    'company': {'type': ['string', 'null']},
                    'location': {'type': ['string', 'null']},
                    'start_date': {'type': ['string', 'null']},
                    'end_date': {'type': ['string', 'null']},
                    'description': {'type': 'array', 'items': {'type': 'string'}},
                    'skills': {'type': 'array', 'items': {'type': 'string'}},
                },
            },
        },
        'projects': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['name', 'description', 'technologies', 'url'],
                'properties': {
                    'name': {'type': ['string', 'null']},
                    'description': {'type': ['string', 'null']},
                    'technologies': {'type': 'array', 'items': {'type': 'string'}},
                    'url': {'type': ['string', 'null']},
                },
            },
        },
        'certifications': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['name', 'issuer', 'date', 'credential_url'],
                'properties': {
                    'name': {'type': ['string', 'null']},
                    'issuer': {'type': ['string', 'null']},
                    'date': {'type': ['string', 'null']},
                    'credential_url': {'type': ['string', 'null']},
                },
            },
        },
        'languages': {'type': 'array', 'items': {'type': 'string'}},
        'keywords': {'type': 'array', 'items': {'type': 'string'}},
        'target_roles': {'type': 'array', 'items': {'type': 'string'}},
    },
}


class InvalidAnalysisData(ValueError):
    pass


def _validate_object(value, fields, path):
    if not isinstance(value, dict):
        raise InvalidAnalysisData(f'{path} must be an object.')
    if set(value) != set(fields):
        raise InvalidAnalysisData(f'{path} has missing or unexpected fields.')


def _validate_optional_text(value, path):
    if value is not None and not isinstance(value, str):
        raise InvalidAnalysisData(f'{path} must be a string or null.')


def _validate_text_list(value, path):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise InvalidAnalysisData(f'{path} must be a list of strings.')


def validate_analysis_data(data):
    top_level_fields = (
        'personal_info', 'summary', 'skills', 'education', 'experience',
        'projects', 'certifications', 'languages', 'keywords',
    )
    if 'target_roles' in data:
        _validate_text_list(data['target_roles'], 'target_roles')
    else:
        data['target_roles'] = []
    _validate_object(data, top_level_fields + ('target_roles',), 'analysis')
    _validate_object(
        data['personal_info'],
        ('name', 'email', 'phone', 'location', 'linkedin', 'github', 'portfolio'),
        'personal_info',
    )
    for field, value in data['personal_info'].items():
        _validate_optional_text(value, f'personal_info.{field}')

    _validate_optional_text(data['summary'], 'summary')
    for field in ('skills', 'languages', 'keywords'):
        _validate_text_list(data[field], field)

    nested_fields = {
        'education': ('degree', 'institution', 'location', 'start_date', 'end_date', 'grade'),
        'experience': ('job_title', 'company', 'location', 'start_date', 'end_date', 'description', 'skills'),
        'projects': ('name', 'description', 'technologies', 'url'),
        'certifications': ('name', 'issuer', 'date', 'credential_url'),
    }
    for collection, fields in nested_fields.items():
        if not isinstance(data[collection], list):
            raise InvalidAnalysisData(f'{collection} must be a list.')
        for index, item in enumerate(data[collection]):
            path = f'{collection}[{index}]'
            _validate_object(item, fields, path)
            for field, value in item.items():
                if collection == 'experience' and field in ('description', 'skills'):
                    _validate_text_list(value, f'{path}.{field}')
                elif collection == 'projects' and field == 'technologies':
                    _validate_text_list(value, f'{path}.{field}')
                else:
                    _validate_optional_text(value, f'{path}.{field}')
    return data