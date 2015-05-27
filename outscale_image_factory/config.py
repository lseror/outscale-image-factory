import os

from ConfigParser import SafeConfigParser, NoSectionError


_DEFAULT_CONFIG_PATH = '/etc/omi-factoryrc'
_GENERAL_SECTION = 'general'

_DEFAULTS = {
    'region': 'eu-west-1',
    'volume-location': 'eu-west-1a',
    'root-dev': '/dev/sda1',
    'image-arch': 'x86_64'
}


_config_dict = None


def load():
    global _config_dict
    if _config_dict is None:
        parser = SafeConfigParser(_DEFAULTS, dict_type=dict)

        config_path = os.path.expanduser('~/.omi-factoryrc')
        parser.read([_DEFAULT_CONFIG_PATH, config_path])

        _config_dict = {}
        for key in _DEFAULTS.keys():
            try:
                value = parser.get(_GENERAL_SECTION, key)
            except NoSectionError:
                value = _DEFAULTS[key]
            _config_dict[key] = value

    return _config_dict
