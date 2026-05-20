
import graphene
from graphene.types.generic import GenericScalar

from .crud import ToolsRegistryCRUD

class ToolEntryType(graphene.ObjectType):
    tool_id = graphene.String()
    tool_metadata = GenericScalar()
    tool_search_description = graphene.String()
    tool_tags = graphene.List(graphene.String)
    tool_type = graphene.String()
    tool_man_page_doc = graphene.String()
    tool_api_spec = GenericScalar()
    tool_custom_actions_dsl_map = GenericScalar()
    default_tool_usage_credentials = GenericScalar()

    tool_execution_mode = graphene.String()
    tool_policy_rule_uri = graphene.String()
    tool_source_code_link = graphene.String()
    tool_service_url = graphene.String()
    tool_system_function_rpc_id = graphene.String()
    tool_validation_policy_rule_uri = graphene.String()
    tool_validation_mode = graphene.String()



class Query(graphene.ObjectType):
    tools = graphene.List(
        ToolEntryType,
        query=GenericScalar(required=True),
        description="Generic MongoDB query for tools"
    )

    def resolve_tools(self, info, query):
        crud: ToolsRegistryCRUD = info.context["crud"]
        return crud.query_tools(query)

schema = graphene.Schema(query=Query)