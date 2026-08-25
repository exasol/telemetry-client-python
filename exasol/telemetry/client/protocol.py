"""
Protocol definition of the messages we're sending to the server.
"""

import dataclasses
import time
import typing as tt

# Version of the protocol
VERSION = "0.2"

# type aliases
Feature = str
ProductName = str
ProductVersion = str

# Timestamp of the measurement
Timestamp = tt.Union[int, float]

# Collection of features accumulated
Features = tt.Dict[Feature, tt.List[Timestamp]]


@dataclasses.dataclass(frozen=True)
class Message:
    """
    Top level message to the server.
    """

    # Version of the protocol this message corresponds to.
    version: str

    # Name of the product ('category' in v0.2 protocol)
    product_name: ProductName

    # Version of the product
    product_version: ProductVersion

    # Current unit timestamp when the message was created
    # (used by the server to get the age of the individual reports)
    timestamp: Timestamp

    # Collection of features we've got so far
    features: Features

    def to_json(self) -> dict:
        return {
            "version": self.version,
            "category": self.product_name,
            "productVersion": self.product_version,
            "timestamp": self.timestamp,
            "features": self.features,
        }

    @classmethod
    def from_features(cls, product_name: ProductName, product_version: ProductVersion, features: Features) -> "Message":
        """
        Construct the message object from collected features.
        We're not deep copy of features, just store the reference of it.
        :param features: collection of features
        :param product_name: name of the product
        :param product_version: version of the product
        :return: Message created
        """
        return Message(
            version=VERSION,
            product_name=product_name,
            product_version=product_version,
            timestamp=get_current_ts(),
            features=features,
        )


def get_current_ts() -> Timestamp:
    """
    Get current timestamp.
    """
    return int(time.time())
