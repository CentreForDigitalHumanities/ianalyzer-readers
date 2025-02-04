from glob import glob
import json
import os
from typing import Union

from ianalyzer_readers.extract import JSON
from ianalyzer_readers.readers.core import Field
from ianalyzer_readers.readers.json import JSONReader


def merge_lines(lines: Union[list, str]) -> str:
    if isinstance(lines, list):
        return "\n".join(lines)
    return lines


class JSONDocumentReader(JSONReader):
    """
    Example reader that would operate on corpora with one json file per document
    """

    data_directory = os.path.join(os.path.dirname(__file__), "data")
    single_document = True

    def sources(self, **kwargs):
        for i in range(1):
            data = json.dumps(
                {
                    "TITLE": "ACT I",
                    "SCENE": {
                        "TITLE": "SCENE I.  A desert place.",
                        "STAGEDIR": [
                            "Thunder and lightning. Enter three Witches",
                            "Exeunt",
                        ],
                        "SPEECH": {
                            "SPEAKER": "First Witch",
                        },
                    },
                }
            )
            yield data.encode('utf-8')

    act = Field("act", JSON("TITLE"))
    character = Field("character", JSON("SCENE", "SPEECH", "SPEAKER"))
    scene = Field("scene", JSON("SCENE", "TITLE"))

    fields = [act, character, scene]


class JSONMultipleDocumentReader(JSONReader):
    """
    Example JSON reader for testing parsing arrays in JSON, using JSON data from https://github.com/tux255/analyzing-shakespeare
    """
    data_directory = os.path.join(os.path.dirname(__file__), "data")
    record_path = ["SCENE", "SPEECH"]
    meta = ["TITLE", ["SCENE", "TITLE"], ["SCENE", "STAGEDIR"]]

    def sources(self, **kwargs):
        for filename in glob(f"{self.data_directory}/*.json"):
            yield filename

    act = Field("act", JSON("TITLE"))
    scene = Field("scene", JSON("SCENE.TITLE"))
    character = Field("character", JSON("SPEAKER"))
    lines = Field("lines", JSON("LINE", transform=merge_lines))
    stage_dir = Field("stage_direction", JSON("SCENE.STAGEDIR", transform=merge_lines))

    fields = [act, scene, character, lines, stage_dir]
