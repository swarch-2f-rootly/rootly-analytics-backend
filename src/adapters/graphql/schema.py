"""
GraphQL schema for the Analytics Service.
Defines the complete GraphQL schema using Strawberry.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from ...core.ports.analytics_service import AnalyticsService
from .resolvers import create_graphql_query


def create_graphql_schema(analytics_service: AnalyticsService, influx_repository, cache_service=None):
    """
    Create the complete GraphQL schema with dependency injection.
    
    Args:
        analytics_service: Implementation of the AnalyticsService port
        influx_repository: Repository for health checks
        cache_service: Cache service for improved performance (optional)
        
    Returns:
        Strawberry GraphQL schema
    """
    # Create query with injected dependencies
    query = create_graphql_query(analytics_service, influx_repository, cache_service)
    
    # Create schema
    schema = strawberry.Schema(query=query)
    
    return schema


def create_graphql_router(
    analytics_service: AnalyticsService,
    influx_repository,
    cache_service=None,
    playground_enabled: bool = False,
    introspection_enabled: bool = True
) -> GraphQLRouter:
    """
    Create GraphQL router with FastAPI integration and playground support.
    
    Args:
        analytics_service: Implementation of the AnalyticsService port
        influx_repository: Repository for health checks
        cache_service: Cache service for improved performance (optional)
        playground_enabled: Whether to enable GraphQL Playground
        introspection_enabled: Whether to enable GraphQL introspection
        
    Returns:
        GraphQL router for FastAPI integration
    """
    schema = create_graphql_schema(analytics_service, influx_repository, cache_service)
    
    # Create and return GraphQL router directly
    return GraphQLRouter(
        schema,
        graphiql=playground_enabled
    )