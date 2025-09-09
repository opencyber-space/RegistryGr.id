import graphene
from graphene.types.generic import GenericScalar

from .crud import FunctionsRegistryCRUD


class FunctionEntryType(graphene.ObjectType):
    function_id = graphene.String()
    function_metadata = GenericScalar()
    function_search_description = graphene.String()
    function_tags = graphene.List(graphene.String)
    function_type = graphene.String()
    function_man_page_doc = graphene.String()
    function_api_spec = GenericScalar()
    func_custom_actions_dsl_map = GenericScalar()
    default_func_usage_credentials = GenericScalar()
    open_api_spec = GenericScalar()
    api_parameters_to_cost_relation_data = GenericScalar()
    is_system_action = graphene.Boolean()


class Query(graphene.ObjectType):
    functions = graphene.List(
        FunctionEntryType,
        query=GenericScalar(required=True),
        description="Generic MongoDB query for functions"
    )

    def resolve_functions(self, info, query):
        crud: FunctionsRegistryCRUD = info.context["crud"]
        return crud.query_functions(query)


schema = graphene.Schema(query=Query)
