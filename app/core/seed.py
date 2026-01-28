"""Database seed script for initial data"""
import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.plan import Plan, BillingCycle
from app.utils.logger import logger


async def check_if_seeded() -> bool:
    """
    Check if database has been seeded
    
    Returns:
        True if database is already seeded, False otherwise
    """
    from sqlalchemy import select
    from sqlalchemy.exc import ProgrammingError
    from asyncpg.exceptions import UndefinedTableError
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if plans exist (plans are always created first)
            result = await session.execute(
                select(Plan).limit(1)
            )
            plan = result.scalar_one_or_none()
            
            # If no plans exist, database is not seeded
            if not plan:
                return False
            
            # Check if analytics data exists (users count)
            from app.models.user import User
            result = await session.execute(
                select(User).limit(1)
            )
            user = result.scalar_one_or_none()
            
            # If no users exist, only plans are seeded (partial seed)
            # Consider it seeded if plans exist (analytics seed is optional)
            return True
    except (ProgrammingError, UndefinedTableError) as e:
        # Check if error is about table not existing (expected before migrations)
        error_str = str(e).lower()
        # Check for "does not exist" which indicates table/relation doesn't exist
        if "does not exist" in error_str:
            # Table doesn't exist yet - this is expected before migrations run
            # Return False (needs seed) without logging as warning
            return False
        # Other database errors should be logged
        logger.warning(f"Database error checking if seeded: {e}")
        return False
    except Exception as e:
        # Check if the underlying exception is about table not existing
        error_str = str(e).lower()
        if "does not exist" in error_str:
            # Table doesn't exist yet - return False without warning
            return False
        logger.warning(f"Error checking if database is seeded: {e}")
        # If we can't check, assume not seeded to be safe
        return False
    except Exception as e:
        logger.warning(f"Error checking if database is seeded: {e}")
        # If we can't check, assume not seeded to be safe
        return False


async def seed_plans(session: AsyncSession):
    """Seed initial plans"""
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.core.config import settings
    
    # Get default tenant (workhub)
    result = await session.execute(
        select(Tenant).where(Tenant.slug == settings.DEFAULT_TENANT_SLUG)
    )
    default_tenant = result.scalar_one_or_none()
    
    if not default_tenant:
        logger.error(f"Default tenant '{settings.DEFAULT_TENANT_SLUG}' not found. Cannot seed plans.")
        raise ValueError(f"Default tenant '{settings.DEFAULT_TENANT_SLUG}' not found")
    
    plans_data = [
        {
            "name": "Day Pass",
            "slug": "day-pass",
            "price": Decimal("49.00"),
            "billing_cycle": BillingCycle.DAILY,
            "description": "Acesso por 1 dia útil (8h às 18h)",
            "features": [
                "Acesso por 1 dia útil (8h às 18h)",
                "Estação de trabalho compartilhada",
                "Wi-Fi de alta velocidade",
                "Café e água à vontade",
                "2 horas de sala de reunião (mediante disponibilidade)",
                "Ideal para: Freelancers, reuniões pontuais"
            ],
            "is_active": True
        },
        {
            "name": "Flex",
            "slug": "flex",
            "price": Decimal("497.00"),
            "billing_cycle": BillingCycle.MONTHLY,
            "description": "10 dias de acesso por mês",
            "features": [
                "10 dias de acesso por mês",
                "Estação de trabalho compartilhada",
                "Wi-Fi de alta velocidade",
                "Café, água e snacks",
                "4 horas de sala de reunião/mês",
                "Armário compartilhado",
                "Acesso à comunidade e eventos",
                "Ideal para: Profissionais híbridos, consultores"
            ],
            "is_active": True
        },
        {
            "name": "Dedicado",
            "slug": "dedicado",
            "price": Decimal("897.00"),
            "billing_cycle": BillingCycle.MONTHLY,
            "description": "Acesso ilimitado (24/7)",
            "features": [
                "Acesso ilimitado (24/7)",
                "Mesa fixa personalizada",
                "Wi-Fi de alta velocidade",
                "Café, água e snacks",
                "10 horas de sala de reunião/mês",
                "Armário privativo",
                "Endereço fiscal",
                "Acesso à comunidade e eventos",
                "Suporte administrativo",
                "Ideal para: Startups, pequenas empresas"
            ],
            "is_active": True
        }
    ]

    created_count = 0
    for plan_data in plans_data:
        # Add tenant_id to plan data
        plan_data["tenant_id"] = default_tenant.id
        
        # Verificar se o plano já existe (verificar por tenant_id + slug)
        result = await session.execute(
            select(Plan).where(
                Plan.tenant_id == default_tenant.id,
                Plan.slug == plan_data["slug"]
            )
        )
        existing_plan = result.scalar_one_or_none()
        
        if not existing_plan:
            plan = Plan(**plan_data)
            session.add(plan)
            created_count += 1
        else:
            logger.debug(f"Plan {plan_data['slug']} already exists for tenant {default_tenant.slug}, skipping")
    
    if created_count > 0:
        await session.commit()
        logger.info(f"Seeded {created_count} new plans")
    else:
        logger.info("All plans already exist, nothing to seed")


async def run_seed():
    """Run all seed functions"""
    async with AsyncSessionLocal() as session:
        try:
            logger.info("Starting database seed...")
            await seed_plans(session)
            
            # Import and run analytics seed
            try:
                from app.core.seed_analytics import seed_analytics_data
                await seed_analytics_data(session)
            except ImportError:
                logger.warning("seed_analytics not available, skipping analytics data")
            except Exception as e:
                logger.warning(f"Error seeding analytics data: {e}")
            
            logger.info("Database seed completed successfully!")
        except Exception as e:
            logger.error(f"Error during seed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())

