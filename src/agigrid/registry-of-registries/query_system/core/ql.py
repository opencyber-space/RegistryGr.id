import graphene
from typing import List
from .controller import QueryController


class RegistrySearchDataType(graphene.ObjectType):
    registry_id = graphene.String()
    registry_type = graphene.String()
    registry_sub_type = graphene.String()
    registry_metadata = graphene.JSONString()
    registry_search_tags = graphene.List(graphene.String)
    registry_search_description = graphene.String()


class RegistryType(graphene.ObjectType):
    registry_id = graphene.String()
    registry_url = graphene.String()
    registry_api_index = graphene.String()
    registry_documentation_s3_url = graphene.String()
    registry_client_sdk_s3_url = graphene.String()
    registry_asset_id = graphene.String()
    health_check_api = graphene.String()
    registry_acl_config_info = graphene.JSONString()
    registry_search_data = graphene.Field(RegistrySearchDataType)


class Query(graphene.ObjectType):
    registry_by_id = graphene.Field(RegistryType, registry_id=graphene.String(required=True))
    registries_by_type = graphene.List(RegistryType, registry_type=graphene.String(required=True))
    registries_by_tags = graphene.List(RegistryType, tags=graphene.List(graphene.String, required=True))
    registries_by_url = graphene.List(RegistryType, url_fragment=graphene.String(required=True))
    registries_by_filter = graphene.List(RegistryType, mongo_filter=graphene.JSONString(), limit=graphene.Int(default_value=100))

    def resolve_registry_by_id(self, info, registry_id):
        qc = QueryController()
        result = qc.get_registry_by_id(registry_id)
        return result

    def resolve_registries_by_type(self, info, registry_type):
        qc = QueryController()
        return qc.find_registries_by_type(registry_type)

    def resolve_registries_by_tags(self, info, tags):
        qc = QueryController()
        return qc.find_registries_by_tags(tags)

    def resolve_registries_by_url(self, info, url_fragment):
        qc = QueryController()
        return qc.find_registries_by_url(url_fragment)

    def resolve_registries_by_filter(self, info, mongo_filter, limit=100):
        import json
        filter_obj = json.loads(mongo_filter) if isinstance(mongo_filter, str) else mongo_filter
        qc = QueryController()
        return qc.query_raw(filter_obj, limit=limit)


schema = graphene.Schema(query=Query)
