import base64
import json
import random
import uuid
from typing import Any, Dict, List, Optional

import requests


class component_names:
    ACTIONS_ROW_COMPONENT = 1
    BUTTON_COMPONENT = 2
    SELECT_MENU_COMPONENT = 3
    TEXT_INPUT_COMPONENT = 4
    USER_SELECT_MENU_COMPONENT = 5
    ROLE_SELECT_MENU_COMPONENT = 6
    MENTIONABLE_SELECT_MENU_COMPONENT = 7
    CHANNEL_SELECT_MENU_COMPONENT = 8
    SECTION_COMPONENT = 9
    TEXT_DISPLAY_COMPONENT = 10
    THUMBNAIL_COMPONENT = 11
    MEDIA_GALLERY_COMPONENT = 12
    FILE_COMPONENT_TYPE = 13
    SEPARATOR_COMPONENT = 14
    CONTAINER_COMPONENT = 17
    LABEL_COMPONENT = 18


BUTTON_STYLES = {
    1: "primary",
    2: "secondary",
    3: "success",
    4: "danger",
    5: "link",
    6: "premium",
}

COMPONENT_NAMES = {
    component_names.ACTIONS_ROW_COMPONENT: "action_row",
    component_names.BUTTON_COMPONENT: "button",
    component_names.SELECT_MENU_COMPONENT: "select_menu",
    component_names.TEXT_INPUT_COMPONENT: "text_input",
    component_names.USER_SELECT_MENU_COMPONENT: "user_select",
    component_names.ROLE_SELECT_MENU_COMPONENT: "role_select",
    component_names.MENTIONABLE_SELECT_MENU_COMPONENT: "mentionable_select",
    component_names.CHANNEL_SELECT_MENU_COMPONENT: "channel_select",
    component_names.SECTION_COMPONENT: "section",
    component_names.TEXT_DISPLAY_COMPONENT: "text_display",
    component_names.THUMBNAIL_COMPONENT: "thumbnail",
    component_names.MEDIA_GALLERY_COMPONENT: "media_gallery",
    component_names.FILE_COMPONENT_TYPE: "file",
    component_names.SEPARATOR_COMPONENT: "separator",
    component_names.CONTAINER_COMPONENT: "container",
    component_names.LABEL_COMPONENT: "label",
}


def get_component_name(component_type: int) -> str:
    return COMPONENT_NAMES.get(component_type, "unknown")


def walker(components: list, message_details: dict = None):
    BUTTONS_LIST = []
    COMPONENTS_LIST = []

    for component in components:
        section_component = False
        component_type = component.get("type")

        if component_type == component_names.BUTTON_COMPONENT:
            BUTTONS_LIST.append(accessory(component, message_details))
        elif component_type == component_names.SELECT_MENU_COMPONENT:
            COMPONENTS_LIST.append(select_menu(component, message_details))
        elif component_type == component_names.SECTION_COMPONENT:
            section_component = True
            COMPONENTS_LIST.append(section(component, message_details))
        elif component_type == component_names.TEXT_DISPLAY_COMPONENT:
            COMPONENTS_LIST.append(text_display(component))
        elif component_type == component_names.THUMBNAIL_COMPONENT:
            COMPONENTS_LIST.append(accessory(component, message_details))
        elif component_type == component_names.MEDIA_GALLERY_COMPONENT:
            COMPONENTS_LIST.append(media_gallery(component))
        elif component_type == component_names.LABEL_COMPONENT:
            COMPONENTS_LIST.append(label(component))

        if not section_component:
            if component.get("components"):
                nested_components_list, nested_buttons_list = walker(
                    component.get("components"), message_details
                )
                COMPONENTS_LIST.extend(nested_components_list)
                BUTTONS_LIST.extend(nested_buttons_list)

            if component.get("accessory"):
                cur_accessory = accessory(component["accessory"], message_details)
                if cur_accessory.component_name != "button":
                    COMPONENTS_LIST.append(cur_accessory)
                else:
                    BUTTONS_LIST.append(cur_accessory)

    return COMPONENTS_LIST, BUTTONS_LIST


class author:
    def __init__(self, data: dict):
        self.name = data.get("username")
        self.id = int(data.get("id", 0))


class emoji:
    def __init__(self, data: dict):
        self.id = int(data.get("id", 0))
        self.name = data.get("name")


class select_menu_options:
    def __init__(self, data: dict):
        self.emoji = emoji(data.get("emoji", {}))
        self.label = data.get("label")
        self.value = data.get("value")
        self.description = data.get("description")


class select_menu:
    def __init__(self, component: dict, message_details: dict):
        self.component_name = COMPONENT_NAMES.get(component["type"])
        self.options = []
        if component.get("options"):
            for item in component.get("options"):
                self.options.append(select_menu_options(item))
        self.custom_id = component.get("custom_id")
        self.placeholder = component.get("placeholder")
        self._message_channel_id = message_details.get("message_channel")
        self._message_id = message_details.get("message_id")
        self._message_flag = message_details.get("message_flag")
        self._author_id = message_details.get("message_author_id")
        self._guild_id = message_details.get("message_guild_id")


class section:
    def __init__(self, component: dict, message_details: dict = None):
        self.component_name = COMPONENT_NAMES.get(component["type"])
        self.accessory = accessory(component.get("accessory", {}), message_details)
        self.components, self.buttons = walker(
            component.get("components", []), message_details
        )


class text_display:
    def __init__(self, component: dict):
        self.component_name = COMPONENT_NAMES.get(component["type"])
        self.id = component.get("id")
        self.content = component.get("content")


class media_gallery_item:
    def __init__(self, data: dict):
        self.media = media(data.get("media", {}))
        self.description = data.get("description")


class media_gallery:
    def __init__(self, component: dict):
        self.component_name = COMPONENT_NAMES.get(component["type"])
        self.items = []
        for item in component.get("items", []):
            self.items.append(media_gallery_item(item))


class label:
    def __init__(self, component: dict):
        self.component_name = COMPONENT_NAMES.get(component["type"])
        self.id = component.get("id")
        self.label = component.get("label")
        self.description = component.get("description")


class media:
    def __init__(self, data: dict):
        self.url = data.get("url")
        self.proxy_url = data.get("proxy_url")
        self.placeholder = data.get("placeholder")


class accessory:
    def __init__(self, data: dict, message_details: dict = None):
        self.component_name = COMPONENT_NAMES.get(data.get("type"))
        self.id = data.get("id")
        self.url = data.get("url")
        self.custom_id = data.get("custom_id")
        self.label = data.get("label")
        self.emoji = emoji(data.get("emoji", {}))
        self.disabled = data.get("disabled", False)
        self.description = data.get("description")
        self.type = int(data.get("type", -1)) if data.get("type") is not None else None
        self.flags = data.get("flags")
        self.style = BUTTON_STYLES.get(data.get("style")) if data.get("style") else None
        self.media = media(data.get("media", {}))

        self.is_link_button = self.component_name == "button" and self.url is not None
        self.is_clickable_button = (
            self.component_name == "button"
            and self.custom_id is not None
            and not self.disabled
        )

        self._message_channel_id = None
        self._message_id = None
        self._message_flag = None
        self._author_id = None
        self._guild_id = None

        if self.is_clickable_button and message_details:
            self._message_channel_id = message_details.get("message_channel")
            self._message_id = message_details.get("message_id")
            self._message_flag = message_details.get("message_flag")
            self._author_id = message_details.get("message_author_id")
            self._guild_id = message_details.get("message_guild_id")

    def click(self, headers: dict, guild_id: Optional[str] = None) -> bool:
        if not self.is_clickable_button:
            return False

        guild_id = guild_id or self._guild_id
        if not guild_id:
            return False

        payload = {
            "type": 3,
            "application_id": str(self._author_id or ""),
            "guild_id": str(guild_id),
            "channel_id": str(self._message_channel_id),
            "message_id": str(self._message_id),
            "session_id": str(uuid.uuid4()),
            "message_flags": int(self._message_flag or 0),
            "data": {"component_type": 2, "custom_id": self.custom_id},
        }

        try:
            r = requests.post(
                "https://discord.com/api/v9/interactions",
                headers=headers,
                json=payload,
                timeout=15,
            )
            return r.status_code == 204
        except Exception:
            return False


class message:
    def __init__(self, data: dict):
        self.author = author(data.get("author", {}))
        self.id = int(data.get("id", 0))
        self.flags = int(data.get("flags", 0))
        self.content = data.get("content", "")
        self.channel_id = int(data.get("channel_id", 0))
        self.guild_id = data.get("guild_id")
        self.components, self.buttons = walker(
            components=data.get("components", []),
            message_details={
                "message_channel": self.channel_id,
                "message_id": self.id,
                "message_flag": self.flags,
                "message_author_id": self.author.id,
                "message_guild_id": self.guild_id,
            },
        )


def get_message_obj(msg: dict) -> message:
    return message(msg)
