import json, requests, toml, yaml, random, string, logging
from typing import Callable
from lsp_map import lsp_map
from subprocess import Popen as run, PIPE
from pathlib import Path

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

DUMP_DIR = '/tmp/lsptmp/'

class Manager:
    # TODO: (Mike): Needs logging ability

    class InvalidConfigException(Exception):
        pass

    class UnknownConfigTypeException(Exception):
        pass

    class LSPInstallationException(Exception):
        pass

    def __init__(self, load_config: dict = None, debug: bool = False) -> None:
        self._debug = False
        self._create_loggers()
        if debug:
            self.toggle_debug()
        Path(DUMP_DIR).mkdir(parents=True, exist_ok=True)
        self._config = dict()
        self._state = dict()
        if load_config:
            self.use_new_config(load_config)
        else:
            self.use_new_config(dict())
        self._load_state()
        self._logger.debug(repr(self))

    def __repr__(self) -> str:
        return f'''<Manager(load_config={self._config}), debug={self._debug})>'''
 
    def _create_loggers(self) -> None:
        self._logger = logging.getLogger('root')
        logging_formatter = logging.Formatter('%(asctime)s %(name)s %(filename)s:%(lineno)d:%(levelname)s: %(message)s')
        self._logger.setLevel(logging.INFO)
        logging_file_handler = logging.FileHandler('/var/log/lspcontainer.log')
        logging_file_handler.setFormatter(logging_formatter)
        logging_file_handler.setLevel(logging.INFO)
        self._logger.addHandler(logging_file_handler)

        logging_stream_handler = logging.StreamHandler()
        logging_stream_handler.setFormatter(logging_formatter)
        logging_stream_handler.setLevel(logging.INFO)
        self._logger.addHandler(logging_stream_handler)

        self._script_logger = logging.getLogger('scripts')
        logging_formatter = logging.Formatter('%(message)s')
        self._script_logger.setLevel(logging.INFO)

        logging_stream_handler = logging.StreamHandler()
        logging_stream_handler.setFormatter(logging_formatter)
        logging_stream_handler.setLevel(logging.INFO)
        self._script_logger.addHandler(logging_stream_handler)

        logging_file_handler = logging.FileHandler('/var/log/lsp-container-installs.log')
        logging_file_handler.setFormatter(logging_formatter)
        logging_file_handler.setLevel(logging.INFO)
        self._script_logger.addHandler(logging_file_handler)

    def start_lsp(self, lsp: str) -> bool:
        return True

    def stop_lsp(self, lsp: str) -> bool:
        return True

    def talk_to_lsp(self, lsp: str, data: str) -> str:
        return ''

    def config_lsp(self, lsp: str, options: dict) -> bool:
        return True

    def restart_lsp(self, lsp: str) -> bool:
        
        return self.stop_lsp(lsp) and self.start_lsp(lsp)

    def toggle_debug(self) -> None:
        log_level = None
        if self._debug:
            log_level = logging.INFO
            self._debug = False
        else:
            log_level = logging.DEBUG
            self._debug = True
        [handler.setLevel(log_level) for handler in self._logger.handlers]
        self._logger.info(f"Set logging level to {logging.getLevelName(log_level)}")

    def install_lsp(self, lsp: str, install_command: str = '') -> bool:
        if install_command:
            pass
            # TODO: (Mike): We should handle if the install will overrite an existing lsp
        if lsp_map[lsp]:
            # We recogonize this lsp
            script = self._download_install_script(lsp_map[lsp])
            if not self._install_script(script):
                raise Manager.LSPInstallationException()
        return True

    def uninstall_lsp(self, lsp: str) -> bool:
        return True

    def dump_config(self) -> str:
        return self._config['dumper'](self._config['conf'])
    def use_new_config(self, config) -> None:
        if config:
            self._logger.info("Loading new config")
            self._logger.debug(config)
        if isinstance(config, dict):
            self._load_config('json', json.dumps, config)
            return
        elif not isinstance(config, str):
            raise Manager.InvalidConfigException("Provided configuration needs to be a string")
        conf_as_dict: dict = dict()
        valid_config_methods = [
            self._try_config_as_string,
            self._try_config_as_file,
            self._try_config_as_url
        ]
        # Iterate through all available options to try and read the config in
        conf_type: str = ''
        conf_dumper: Callable = None
        conf_as_dict: dict = dict()
        for method in valid_config_methods:
            try:
                conf_type, conf_dumper, conf_as_dict = method(config)
            except Exception as exception:
                continue
        
        if not conf_type:
            # TODO: (Mike): Should we die here or complain and load a default?
            raise Manager.UnknownConfigTypeException()
        self._load_config(conf_type, conf_dumper, conf_as_dict)

    def _try_config_as_json(self, config: str) -> tuple:
        return 'json', json.dumps, json.loads(config)

    def _try_config_as_toml(self, config: str) -> tuple:
        return 'toml', toml.dumps, toml.loads(config)

    def _try_config_as_yaml(self, config: str) -> tuple:
        dumper = lambda data: yaml.dump(data, Dumper=Dumper)
        return 'yaml', dumper, yaml.load(config, Loader=Loader)

    def _try_config_as_string(self, config: str) -> tuple:
        valid_config_methods = [
            self._try_config_as_toml,
            self._try_config_as_json,
            self._try_config_as_yaml
        ]
        for method in valid_config_methods:
            try:
                return method(config)
            except Exception as exception:
                continue
        return None, None

    def _try_config_as_file(self, config: str) -> tuple:
        with open(config, 'r') as _in_file:
            content = ''.join(_in_file.readlines())
            return self._try_config_as_string(content)

    def _try_config_as_url(self, config: str) -> tuple:
        response = requests.get(config)
        return self._try_config_as_string(response.content.decode('utf8'))

    def _load_config(self, conf_type: str, dumper: Callable, config: dict) -> None:
        self._config = dict(_type=conf_type, dumper=dumper, conf=config)

    def _download_install_script(self, script: str) -> Path:
        print(f"Trying to download {script}")
        try:
            response = requests.get(script)
            file_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
            file_name = Path(DUMP_DIR) / file_name
            with open(file_name, 'w') as _out_file:
                _out_file.write(response.content.decode('utf8'))
            file_name.chmod(0o774)
            print(f'Downloaded to {str(file_name)}')
            return file_name
        except Exception as exception:
            print(repr(exception))

            pass
        return None
    def _install_script(self, script: Path) -> bool:
        with run([script], stdout=PIPE, stderr=PIPE, encoding='utf-8', shell=True) as process:
            while not process.returncode:
                pass
                # line = process.stdout.readline().rstrip()
                # self._script_logger.info(line)
                # self._logger.debug(line)
        # result = run([script], shell=True, check=True, stdout=PIPE, stderr=PIPE)
        return True

    def _load_state(self) -> None:
        pass
