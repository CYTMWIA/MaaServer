import functools
import tomllib

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    maacore_path: str = Field()

    adb_path: str = Field()
    adb_addr: str = Field()

    bark_key: str = Field()


@functools.cache
def settings(path="settings.toml"):
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return Settings.model_validate(raw)
