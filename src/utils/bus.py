from src.gui.custom_widgets.flow_layout import FlowScrollArea

class Storage:
    def __init__(self) -> None:
        self._subscribers: list[tuple[str, object]] = []

    def add(self, key_name:str, object_instance:object):
        new_entry: tuple[str, object] = (key_name, object_instance)
        self._subscribers.append(new_entry)

    def _objects_to_dict(self) -> dict[str, str | list[str]]:
        def _object_to_data(object_instance: object) -> str | list[str]:
            if hasattr(object_instance, "text"):
                return object_instance.text() # type: ignore
            match object_instance:
                case str():
                    return object_instance
                case int():
                    return str(object_instance)
                case FlowScrollArea():
                    items = []
                    widgets = object_instance.getWidgets()
                    for widget in widgets:
                        item = _object_to_data(widget)
                        if not item or item == "":
                            continue
                        items.append(item)
                    return items
                case _:
                    return ""

        output:dict[str, str | list[str]] = {}
        for pair in self._subscribers:
            key_name, object_instance = pair
            widget_contents = _object_to_data(object_instance)
            if not widget_contents or widget_contents == "" or widget_contents == []:
                continue
            if not key_name or key_name == "":
                print("WARNING: Passed a empty key_name for contents", f"'{widget_contents}'")
                continue
            output[key_name] = widget_contents
        return output

    def get_data(self) -> dict[str, str | list[str]]:
        return self._objects_to_dict()

storage = Storage()
