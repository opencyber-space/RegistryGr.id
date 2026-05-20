import logging
import graphene
from graphene.types.generic import GenericScalar

from .schema import Asset

from typing import Optional, List, Dict, Any


logger = logging.getLogger("AssetQuery")
logger.setLevel(logging.INFO)

class AssetQuery:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, asset_id: str) -> Optional[Asset]:
        try:
            return self.db.find_by_id(asset_id)
        except Exception as e:
            logger.error(f"get_by_id failed: {e}")
            return None

    def get_by_type(self, asset_type: str) -> List[Asset]:
        try:
            cursor = self.db.collection.find({"profiles.asset_type": asset_type})
            return [Asset.from_dict(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"get_by_type failed: {e}")
            return []

    def get_by_sub_type(self, sub_type: str) -> List[Asset]:
        try:
            cursor = self.db.collection.find({"profiles.asset_sub_type": sub_type})
            return [Asset.from_dict(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"get_by_sub_type failed: {e}")
            return []

    def get_by_tag(self, tag: str) -> List[Asset]:
        try:
            cursor = self.db.collection.find({"profiles.asset_tags": tag})
            return [Asset.from_dict(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"get_by_tag failed: {e}")
            return []

    def get_by_api_route(self, route: str) -> List[Asset]:
        try:
            cursor = self.db.collection.find({"apis.asset_api_route": route})
            return [Asset.from_dict(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"get_by_api_route failed: {e}")
            return []

    def search(self, query_dict: Dict[str, Any]) -> List[Asset]:
        try:
            cursor = self.db.collection.find(query_dict)
            return [Asset.from_dict(doc) for doc in cursor]
        except Exception as e:
            logger.error(f"search failed: {e}")
            return []


class AssetType(graphene.ObjectType):
    asset_id = graphene.String()
    asset_uri = graphene.String()
    asset_version = graphene.String()
    asset_profile_id = graphene.String()
    asset_file_ids = graphene.List(graphene.String)
    asset_brief_description = graphene.String()
    profiles = GenericScalar()
    policies = GenericScalar()
    files = GenericScalar()
    apis = GenericScalar()
    index_mappings = GenericScalar()


class Query(graphene.ObjectType):
    get_asset_by_id = graphene.Field(AssetType, asset_id=graphene.String(required=True))
    get_assets_by_type = graphene.List(AssetType, asset_type=graphene.String(required=True))
    get_assets_by_tag = graphene.List(AssetType, tag=graphene.String(required=True))
    get_assets_by_sub_type = graphene.List(AssetType, sub_type=graphene.String(required=True))
    get_assets_by_api_route = graphene.List(AssetType, route=graphene.String(required=True))
    search_assets = graphene.List(AssetType, filters=GenericScalar(required=True))

    def resolve_get_asset_by_id(self, info, asset_id):
        return info.context["query"].get_by_id(asset_id)

    def resolve_get_assets_by_type(self, info, asset_type):
        return info.context["query"].get_by_type(asset_type)

    def resolve_get_assets_by_tag(self, info, tag):
        return info.context["query"].get_by_tag(tag)

    def resolve_get_assets_by_sub_type(self, info, sub_type):
        return info.context["query"].get_by_sub_type(sub_type)

    def resolve_get_assets_by_api_route(self, info, route):
        return info.context["query"].get_by_api_route(route)

    def resolve_search_assets(self, info, filters):
        return info.context["query"].search(filters)

schema = graphene.Schema(query=Query)
