from __future__ import annotations

import json
import unittest

from modora.core.infra.ocr.paddle import PaddleOCRAPIClient


class PaddleApiPageParsingTest(unittest.TestCase):
    def test_parse_payload_splits_layout_parsing_results_by_position(self) -> None:
        client = PaddleOCRAPIClient.__new__(PaddleOCRAPIClient)
        body = json.dumps(
            {
                "errorCode": 0,
                "result": {
                    "layoutParsingResults": [
                        {
                            "inputImage": "https://example.com/input_img_0.jpg",
                            "prunedResult": {"parsing_res_list": [{"block_id": 0}]},
                        },
                        {
                            "inputImage": "https://example.com/input_img_1.jpg",
                            "prunedResult": {"parsing_res_list": [{"block_id": 1}]},
                        },
                        {
                            "inputImage": "https://example.com/input_img_2.jpg",
                            "prunedResult": {"parsing_res_list": [{"block_id": 2}]},
                        },
                    ]
                },
            }
        )

        pages = client._parse_jsonl_payload(body)

        self.assertEqual([page_id for page_id, _ in pages], [1, 2, 3])
        self.assertEqual(
            [page["inputImage"] for _, page in pages],
            [
                "https://example.com/input_img_0.jpg",
                "https://example.com/input_img_1.jpg",
                "https://example.com/input_img_2.jpg",
            ],
        )

    def test_parse_payload_keeps_nested_pages_as_fallback(self) -> None:
        client = PaddleOCRAPIClient.__new__(PaddleOCRAPIClient)
        body = json.dumps(
            {
                "result": {
                    "pages": [
                        {"page_id": 2, "layoutParsingResults": []},
                        {"page_id": 4, "layoutParsingResults": []},
                    ]
                }
            }
        )

        pages = client._parse_jsonl_payload(body)

        self.assertEqual([page_id for page_id, _ in pages], [2, 4])

    def test_parse_page_uses_pruned_result_for_split_page_entry(self) -> None:
        client = PaddleOCRAPIClient.__new__(PaddleOCRAPIClient)
        page = {
            "inputImage": "https://example.com/input_img_0.jpg",
            "markdown": "# fallback",
            "prunedResult": {
                "parsing_res_list": [
                    {
                        "block_id": 7,
                        "block_label": "text",
                        "block_content": "hello world",
                        "block_bbox": [100, 200, 300, 400],
                    }
                ]
            },
        }

        blocks = client._parse_page(page, page_id=2)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].page_id, 2)
        self.assertEqual(blocks[0].block_id, 7)
        self.assertEqual(blocks[0].label, "text")
        self.assertEqual(blocks[0].content, "hello world")
        self.assertEqual(blocks[0].bbox, [50.0, 100.0, 150.0, 200.0])


if __name__ == "__main__":
    unittest.main()
