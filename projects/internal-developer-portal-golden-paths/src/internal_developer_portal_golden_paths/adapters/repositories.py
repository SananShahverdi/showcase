from typing import List, Dict, Optional
from internal_developer_portal_golden_paths.domain.models import ServiceMetadata, TemplateDefinition, TemplateStatus

class CatalogStore:
    def __init__(self):
        self.services: Dict[str, ServiceMetadata] = {}
        self.templates: Dict[str, TemplateDefinition] = {
            "fastapi-base": TemplateDefinition(
                id="fastapi-base",
                name="FastAPI Microservice",
                version="1.0.0",
                description="Golden path for Python FastAPI services",
                status=TemplateStatus.APPROVED,
                parameters={"service_name": "string", "port": "int"}
            ),
            "node-base": TemplateDefinition(
                id="node-base",
                name="Node.js Express",
                version="1.0.0",
                description="Golden path for Node services",
                status=TemplateStatus.APPROVED,
                parameters={"service_name": "string", "port": "int"}
            ),
            "react-base": TemplateDefinition(
                id="react-base", name="React Web App", version="1.0.0",
                description="Vite React web application with build and smoke test",
                status=TemplateStatus.APPROVED, parameters={"service_name": "string", "port": "int"}
            ),
            "worker-base": TemplateDefinition(
                id="worker-base", name="Python Worker", version="1.0.0",
                description="Python background worker with deterministic local runner",
                status=TemplateStatus.APPROVED, parameters={"service_name": "string"}
            ),
            "scheduled-job-base": TemplateDefinition(
                id="scheduled-job-base", name="Scheduled Python Job", version="1.0.0",
                description="One-shot Python job ready for an external scheduler",
                status=TemplateStatus.APPROVED, parameters={"service_name": "string"}
            )
        }
        
    def add_service(self, service: ServiceMetadata):
        if any(existing.name == service.name for existing in self.services.values()):
            raise ValueError(f"Service name {service.name} is already registered")
        self.services[service.id] = service
        
    def get_services(self) -> List[ServiceMetadata]:
        return list(self.services.values())

    def get_service(self, service_id: str) -> Optional[ServiceMetadata]:
        return self.services.get(service_id)
        
    def get_template(self, template_id: str) -> Optional[TemplateDefinition]:
        return self.templates.get(template_id)
        
    def get_templates(self) -> List[TemplateDefinition]:
        return list(self.templates.values())

    def add_template(self, template: TemplateDefinition):
        if template.id in self.templates:
            raise ValueError("Template ID already exists; create a new versioned ID")
        self.templates[template.id] = template

    def save_template(self, template: TemplateDefinition):
        self.templates[template.id] = template
