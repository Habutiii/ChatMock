from __future__ import annotations

import unittest
from unittest.mock import patch

from chatmock.utils import add_pdf_page_images_to_responses_input


class PdfVisionInputTests(unittest.TestCase):
    @patch("chatmock.utils.render_pdf_file_data_to_images")
    def test_adds_rendered_pages_after_base64_pdf_input_file(self, mock_render) -> None:
        mock_render.return_value = ["data:image/png;base64,cGFnZTE=", "data:image/png;base64,cGFnZTI="]
        pdf_part = {
            "type": "input_file",
            "filename": "report.pdf",
            "file_data": "data:application/pdf;base64,JVBERi0=",
        }

        actual = add_pdf_page_images_to_responses_input(
            [{"type": "message", "role": "user", "content": [pdf_part]}]
        )

        self.assertEqual(
            actual[0]["content"],
            [
                pdf_part,
                {"type": "input_image", "image_url": "data:image/png;base64,cGFnZTE="},
                {"type": "input_image", "image_url": "data:image/png;base64,cGFnZTI="},
            ],
        )
        mock_render.assert_called_once_with(pdf_part["file_data"])
