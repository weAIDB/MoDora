from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from modora.core.domain import Component, ComponentPack, Location
from modora.core.services.constructor import TreeConstructor
from modora.core.settings import Settings


class ConstructorLocationTest(unittest.TestCase):
    def test_container_text_node_preserves_all_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_path = root / "config.json"
            cfg_path.write_text(
                '{"docs_dir": "' + str(root / "docs") + '", "cache_dir": "' + str(root / "cache") + '"}',
                encoding="utf-8",
            )
            settings = Settings.load(str(cfg_path))

            cp = ComponentPack(
                body=[
                    Component(
                        type="text",
                        title="Section A",
                        title_level=1,
                        data="Section A\nintro and nested content",
                        location=[
                            Location(bbox=[0, 0, 10, 10], page=1),
                            Location(bbox=[0, 10, 100, 100], page=1),
                        ],
                    ),
                    Component(
                        type="text",
                        title="Subsection A.1",
                        title_level=2,
                        data="Subsection body",
                        location=[Location(bbox=[10, 20, 40, 40], page=1)],
                    ),
                ]
            )

            tree = TreeConstructor(settings, logging.getLogger("test")).construct_tree(cp)
            parent = tree.root.children["Section A"]

            self.assertEqual(parent.type, "text")
            self.assertEqual(len(parent.location), 2)
            self.assertEqual(parent.location[0].bbox, [0, 0, 10, 10])
            self.assertEqual(parent.location[1].bbox, [0, 10, 100, 100])


if __name__ == "__main__":
    unittest.main()
