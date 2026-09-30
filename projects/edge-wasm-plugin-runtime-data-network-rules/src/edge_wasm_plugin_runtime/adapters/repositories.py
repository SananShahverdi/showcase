from typing import Dict, List, Optional

from edge_wasm_plugin_runtime.domain.models import Plugin


class PluginRepository:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}

    def save_plugin(self, plugin: Plugin) -> None:
        self.plugins[plugin.id] = plugin

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self.plugins.get(plugin_id)

    def get_all(self) -> List[Plugin]:
        return [self.plugins[key] for key in sorted(self.plugins)]
