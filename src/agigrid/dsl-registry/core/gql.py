import graphene
from graphene import ObjectType, String, List, Field, JSONString

from .controllers import SpecDatabase, TemplateDatabase, WorkflowDatabase

spec_db = SpecDatabase()
template_db = TemplateDatabase()
workflow_db = WorkflowDatabase()


# --------- Object Types ---------

class SpecType(graphene.ObjectType):
    spec_uri = String()
    spec_name = String()
    spec_type = String()
    spec_description = String()
    spec_metadata = JSONString()
    spec_data = JSONString()
    backend_policy_rule_ids = JSONString()


class TemplateType(graphene.ObjectType):
    template_id = String()
    template_description = String()
    template_metadata = JSONString()
    template_data = JSONString()
    template_custom_validation_policy_rule_uri = String()


class WorkflowType(graphene.ObjectType):
    workflow_uri = String()
    workflow_name = String()
    workflow_type = String()
    workflow_sub_type = String()
    workflow_description = String()
    workflow_spec_ids = List(String)
    workflow_metadata = JSONString()
    workflow_graph_data = JSONString()


# --------- Query Root ---------

class Query(ObjectType):
    all_specs = List(SpecType)
    all_templates = List(TemplateType)
    all_workflows = List(WorkflowType)

    spec_by_uri = Field(SpecType, spec_uri=String(required=True))
    template_by_id = Field(TemplateType, template_id=String(required=True))
    workflow_by_uri = Field(WorkflowType, workflow_uri=String(required=True))

    def resolve_all_specs(self, info):
        success, result = spec_db.query({})
        return result if success else []

    def resolve_all_templates(self, info):
        success, result = template_db.query({})
        return result if success else []

    def resolve_all_workflows(self, info):
        success, result = workflow_db.query({})
        return result if success else []

    def resolve_spec_by_uri(self, info, spec_uri):
        success, result = spec_db.get_by_spec_uri(spec_uri)
        return result if success else None

    def resolve_template_by_id(self, info, template_id):
        success, result = template_db.get_by_template_id(template_id)
        return result if success else None

    def resolve_workflow_by_uri(self, info, workflow_uri):
        success, result = workflow_db.get_by_workflow_uri(workflow_uri)
        return result if success else None


schema = graphene.Schema(query=Query)
