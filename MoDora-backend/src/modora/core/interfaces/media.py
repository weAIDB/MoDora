from typing import Protocol

from modora.core.domain.component import Component


class ImageProvider(Protocol):
    """Image provider interface protocol.

    Defines the standard interface for obtaining image data from source files (e.g., PDFs).
    """

    def crop_image(self, source: str, component: Component) -> str:
        """Crop an image from the source file based on the component's position information.

        Args:
            source: The source file path or identifier.
            component: The component object containing position information.

        Returns:
            str: Base64 encoded image string.
        """
        ...
