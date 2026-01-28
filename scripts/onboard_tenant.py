#!/usr/bin/env python3
"""
Tenant Onboarding Script

This script automates the process of creating and configuring a new tenant
with all necessary data (plans, prompts, knowledge base).

Usage:
    python scripts/onboard_tenant.py --config config.json
    python scripts/onboard_tenant.py --slug mycompany --name "My Company"
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
import bcrypt
import uuid

from app.core.database import AsyncSessionLocal
from app.models import (
    Tenant, TenantStatus, PromptTemplate, PromptType,
    KnowledgeDocument, DocumentType, Plan, BillingCycle
)


class TenantOnboarder:
    """Class to handle tenant onboarding"""

    def __init__(self):
        self.db = None
        self.tenant = None
        self.api_key = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.db = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.db:
            await self.db.close()

    async def create_tenant(
        self,
        slug: str,
        name: str,
        config: dict = None,
        status: str = "active"
    ) -> Tenant:
        """
        Create a new tenant.

        Args:
            slug: URL-safe identifier
            name: Display name
            config: Configuration dictionary
            status: Tenant status (active, trial, suspended, cancelled)

        Returns:
            Created Tenant object
        """
        print(f"\n📦 Creating tenant: {slug}")

        # Check if tenant already exists
        result = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"❌ Tenant '{slug}' already exists!")
            raise ValueError(f"Tenant '{slug}' already exists")

        # Generate API key
        self.api_key = f"{slug[:2]}_{uuid.uuid4().hex[:32]}"
        api_key_hash = bcrypt.hashpw(self.api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        api_key_prefix = self.api_key[:8]

        # Default config if not provided
        if config is None:
            config = {
                "business_type": "general",
                "currency": "BRL",
                "features": {
                    "enable_handoff": True,
                    "enable_analytics": True
                },
                "funnel_config": {
                    "stages": [
                        {"key": "awareness", "name": "Conscientização"},
                        {"key": "interest", "name": "Interesse"},
                        {"key": "consideration", "name": "Consideração"},
                        {"key": "negotiation", "name": "Negociação"},
                        {"key": "closed_won", "name": "Fechado Ganho"},
                        {"key": "closed_lost", "name": "Perdido"}
                    ]
                },
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "temperature": 0.7
                }
            }

        # Create tenant
        self.tenant = Tenant(
            id=uuid.uuid4(),
            slug=slug,
            name=name,
            config=config,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            status=TenantStatus(status)
        )

        self.db.add(self.tenant)
        await self.db.commit()
        await self.db.refresh(self.tenant)

        print(f"✅ Tenant created: {self.tenant.id}")
        return self.tenant

    async def create_plans(self, plans_data: list) -> list:
        """
        Create plans for tenant.

        Args:
            plans_data: List of plan dictionaries

        Returns:
            List of created Plan objects
        """
        if not plans_data:
            print("\n⏭️  No plans to create")
            return []

        print(f"\n📋 Creating {len(plans_data)} plans...")

        created_plans = []
        for plan_data in plans_data:
            plan = Plan(
                id=uuid.uuid4(),
                tenant_id=self.tenant.id,
                name=plan_data["name"],
                slug=plan_data["slug"],
                price=plan_data["price"],
                billing_cycle=BillingCycle(plan_data["billing_cycle"].lower()),
                features=plan_data.get("features", []),
                description=plan_data.get("description"),
                is_active=plan_data.get("is_active", True)
            )
            self.db.add(plan)
            created_plans.append(plan)
            print(f"  ✅ Plan: {plan.name} (R${plan.price}/{plan.billing_cycle.value})")

        await self.db.commit()
        return created_plans

    async def create_prompts(self, prompts_data: dict) -> list:
        """
        Create prompts for tenant.

        Args:
            prompts_data: Dictionary mapping prompt_type to content

        Returns:
            List of created PromptTemplate objects
        """
        if not prompts_data:
            print("\n⏭️  No custom prompts provided (will use defaults)")
            return []

        print(f"\n💬 Creating {len(prompts_data)} prompts...")

        created_prompts = []
        for prompt_type_str, content in prompts_data.items():
            try:
                prompt_type = PromptType(prompt_type_str.lower())
            except ValueError:
                print(f"  ⚠️  Unknown prompt type: {prompt_type_str}, skipping")
                continue

            prompt = PromptTemplate(
                id=uuid.uuid4(),
                tenant_id=self.tenant.id,
                prompt_type=prompt_type,
                version=1,
                system_prompt=content,
                is_active=True
            )
            self.db.add(prompt)
            created_prompts.append(prompt)
            print(f"  ✅ Prompt: {prompt_type.value}")

        await self.db.commit()
        return created_prompts

    async def create_knowledge_documents(self, docs_data: list) -> list:
        """
        Create knowledge documents for tenant.

        Args:
            docs_data: List of knowledge document dictionaries

        Returns:
            List of created KnowledgeDocument objects
        """
        if not docs_data:
            print("\n⏭️  No knowledge documents to create")
            return []

        print(f"\n📚 Creating {len(docs_data)} knowledge documents...")

        created_docs = []
        for doc_data in docs_data:
            document = KnowledgeDocument(
                id=uuid.uuid4(),
                tenant_id=self.tenant.id,
                title=doc_data["title"],
                slug=doc_data["slug"],
                content=doc_data["content"],
                document_type=DocumentType(doc_data["document_type"].lower()),
                is_active=doc_data.get("is_active", True)
            )
            self.db.add(document)
            created_docs.append(document)
            print(f"  ✅ Document: {document.title} ({document.document_type.value})")

        await self.db.commit()
        return created_docs

    async def onboard(self, config: dict):
        """
        Complete onboarding process.

        Args:
            config: Configuration dictionary with all tenant data
        """
        try:
            # Create tenant
            await self.create_tenant(
                slug=config["slug"],
                name=config["name"],
                config=config.get("config"),
                status=config.get("status", "active")
            )

            # Create plans
            if "plans" in config:
                await self.create_plans(config["plans"])

            # Create prompts
            if "prompts" in config:
                await self.create_prompts(config["prompts"])

            # Create knowledge documents
            if "knowledge_documents" in config:
                await self.create_knowledge_documents(config["knowledge_documents"])

            # Print success summary
            self.print_summary()

        except Exception as e:
            print(f"\n❌ Error during onboarding: {e}")
            await self.db.rollback()
            raise

    def print_summary(self):
        """Print onboarding summary with credentials"""
        print("\n" + "=" * 80)
        print("✅ TENANT ONBOARDING COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nTenant ID:     {self.tenant.id}")
        print(f"Tenant Slug:   {self.tenant.slug}")
        print(f"Tenant Name:   {self.tenant.name}")
        print(f"Status:        {self.tenant.status.value}")
        print(f"\n🔑 API KEY:    {self.api_key}")
        print(f"   (Prefix:    {self.tenant.api_key_prefix}...)")
        print("\n⚠️  SAVE THIS API KEY! It will not be shown again.")
        print("\n" + "-" * 80)
        print("TEST CURL COMMAND:")
        print("-" * 80)
        print(f"""
curl -X POST http://localhost:8000/api/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "X-Tenant-ID: {self.tenant.slug}" \\
  -H "X-API-Key: {self.api_key}" \\
  -d '{{
    "message": "Olá!",
    "user_key": "test_user_1",
    "user_name": "Test User"
  }}'
""")
        print("=" * 80 + "\n")


async def onboard_from_config(config_path: str):
    """
    Onboard tenant from config file.

    Args:
        config_path: Path to JSON config file
    """
    print(f"📄 Loading config from: {config_path}")

    # Load config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Validate required fields
    required_fields = ["slug", "name"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field in config: {field}")

    # Onboard
    async with TenantOnboarder() as onboarder:
        await onboarder.onboard(config)


async def onboard_simple(slug: str, name: str):
    """
    Simple onboarding with minimal data.

    Args:
        slug: Tenant slug
        name: Tenant name
    """
    config = {
        "slug": slug,
        "name": name,
        "status": "active"
    }

    async with TenantOnboarder() as onboarder:
        await onboarder.onboard(config)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Onboard a new tenant to the WorkHub platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Onboard from config file
  python scripts/onboard_tenant.py --config examples/tenant_config.json

  # Simple onboarding (minimal data)
  python scripts/onboard_tenant.py --slug mycompany --name "My Company"
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to JSON config file"
    )

    parser.add_argument(
        "--slug",
        type=str,
        help="Tenant slug (URL-safe identifier)"
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Tenant name (display name)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.config:
        # Config file mode
        asyncio.run(onboard_from_config(args.config))
    elif args.slug and args.name:
        # Simple mode
        asyncio.run(onboard_simple(args.slug, args.name))
    else:
        parser.print_help()
        print("\n❌ Error: Either --config or both --slug and --name are required")
        sys.exit(1)


if __name__ == "__main__":
    main()
