import graphene
from graphene import ObjectType, String, List, Field, Dict as GrapheneDict
from graphene.types.generic import GenericScalar
from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
from bson import ObjectId


class OrgObjectType(graphene.ObjectType):
    org_uri = String()
    org_id = String()
    org_spec_id = String()
    org_local_db_url = String()
    org_service_gateway_url = String()
    org_asset_registry_id = String()
    org_group_ids = List(String)
    org_name = String()
    org_description = String()
    org_metadata = GenericScalar()
    org_url_map = GenericScalar()
    org_tags = List(String)
    org_spec_data = GenericScalar()


class Query(ObjectType):
    orgs = graphene.List(
        OrgObjectType,
        org_id=String(),
        org_spec_id=String(),
        org_name=String(),
        org_asset_registry_id=String(),
        tag=String()
    )

    def resolve_orgs(root, info, **kwargs):
        mongo_uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        client = MongoClient(mongo_uri)
        collection = client["orgs"]["orgs"]

        query = {}
        if "org_id" in kwargs:
            query["org_id"] = kwargs["org_id"]
        if "org_spec_id" in kwargs:
            query["org_spec_id"] = kwargs["org_spec_id"]
        if "org_name" in kwargs:
            query["org_name"] = {"$regex": kwargs["org_name"], "$options": "i"}
        if "org_asset_registry_id" in kwargs:
            query["org_asset_registry_id"] = kwargs["org_asset_registry_id"]
        if "tag" in kwargs:
            query["org_tags"] = kwargs["tag"]

        docs = collection.find(query)
        results = []
        for doc in docs:
            doc.pop("_id", None)
            results.append(OrgObjectType(**doc))
        return results


schema = graphene.Schema(query=Query)
