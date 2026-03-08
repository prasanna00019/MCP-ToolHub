"""
Monitor: Database statistics and monitoring.
Phase 6A: get_database_stats
"""

import time
from typing import Dict, List, Optional, Any
from src.database import get_connection


def _format_result(
    status: str,
    operation: str,
    duration_ms: float = 0,
    result: Any = None,
    message: str = "",
    warnings: List[str] = None,
) -> Dict:
    """Format operation result in standard format."""
    return {
        "status": status,
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "result": result,
        "message": message,
        "warnings": warnings or [],
    }


def get_database_stats(stat_type: str = "summary") -> Dict:
    """
    Get database statistics and monitoring information.
    
    Args:
        stat_type: Type of statistics to retrieve:
            - "summary": General database overview
            - "size": Database and table sizes
            - "connections": Active connection information
            - "cache_hit_ratio": Cache performance metrics
            - "slow_queries": Currently running slow queries
            - "locks": Active locks and blocking queries
            - "all": All statistics combined
        
    Returns:
        Dictionary with requested statistics
        
    Examples:
        get_database_stats("summary")
        get_database_stats("size")
        get_database_stats("connections")
    """
    start_time = time.time()
    warnings = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        valid_types = ["summary", "size", "connections", "cache_hit_ratio", "slow_queries", "locks", "all"]
        if stat_type.lower() not in valid_types:
            return _format_result(
                status="error",
                operation="get_database_stats",
                message=f"Invalid stat_type '{stat_type}'. Must be one of: {', '.join(valid_types)}"
            )
        
        result = {}
        
        # Summary statistics
        if stat_type.lower() in ["summary", "all"]:
            cursor.execute("""
                SELECT 
                    current_database() as database_name,
                    pg_size_pretty(pg_database_size(current_database())) as database_size,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT count(*) FROM pg_stat_activity) as total_connections,
                    version() as postgresql_version,
                    current_setting('server_version') as server_version,
                    current_setting('max_connections') as max_connections
            """)
            
            summary = cursor.fetchone()
            result["summary"] = {
                "database_name": summary[0],
                "database_size": summary[1],
                "active_connections": summary[2],
                "total_connections": summary[3],
                "max_connections": summary[6],
                "postgresql_version": summary[5],
                "uptime_info": f"PostgreSQL {summary[5]}"
            }
            
            # Add table count
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """)
            result["summary"]["table_count"] = cursor.fetchone()[0]
        
        # Size statistics
        if stat_type.lower() in ["size", "all"]:
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as total_size,
                    pg_database_size(current_database()) as total_size_bytes
            """)
            
            db_size = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size,
                    pg_total_relation_size(schemaname||'.'||tablename) as total_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 20
            """)
            
            tables = cursor.fetchall()
            
            result["size"] = {
                "database_size": db_size[0],
                "database_size_bytes": db_size[1],
                "largest_tables": [
                    {
                        "schema": t[0],
                        "table": t[1],
                        "total_size": t[2],
                        "table_size": t[3],
                        "indexes_size": t[4]
                    }
                    for t in tables
                ]
            }
        
        # Connection statistics
        if stat_type.lower() in ["connections", "all"]:
            cursor.execute("""
                SELECT 
                    state,
                    COUNT(*) as count,
                    MAX(EXTRACT(EPOCH FROM (now() - state_change))) as max_duration_seconds
                FROM pg_stat_activity
                WHERE pid != pg_backend_pid()
                GROUP BY state
                ORDER BY count DESC
            """)
            
            conn_states = cursor.fetchall()
            
            cursor.execute("""
                SELECT 
                    client_addr,
                    COUNT(*) as connection_count,
                    array_agg(DISTINCT usename) as users
                FROM pg_stat_activity
                WHERE client_addr IS NOT NULL
                GROUP BY client_addr
                ORDER BY connection_count DESC
            """)
            
            conn_by_client = cursor.fetchall()
            
            cursor.execute("SELECT current_setting('max_connections')::int")
            max_conn = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pg_stat_activity")
            current_conn = cursor.fetchone()[0]
            
            result["connections"] = {
                "current_connections": current_conn,
                "max_connections": max_conn,
                "connection_usage_percent": round((current_conn / max_conn) * 100, 2),
                "by_state": [
                    {
                        "state": state if state else "unknown",
                        "count": count,
                        "max_duration_seconds": round(duration, 2) if duration else 0
                    }
                    for state, count, duration in conn_states
                ],
                "by_client": [
                    {
                        "client_ip": str(addr),
                        "connection_count": count,
                        "users": users
                    }
                    for addr, count, users in conn_by_client
                ]
            }
            
            if current_conn > max_conn * 0.8:
                warnings.append(f"Connection usage is high: {current_conn}/{max_conn} ({result['connections']['connection_usage_percent']}%)")
        
        # Cache hit ratio
        if stat_type.lower() in ["cache_hit_ratio", "all"]:
            cursor.execute("""
                SELECT 
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    CASE 
                        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
                        ELSE (sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read))) * 100 
                    END as cache_hit_ratio
                FROM pg_statio_user_tables
            """)
            
            cache_data = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    sum(idx_blks_read) as index_read,
                    sum(idx_blks_hit) as index_hit,
                    CASE 
                        WHEN sum(idx_blks_hit) + sum(idx_blks_read) = 0 THEN 0
                        ELSE (sum(idx_blks_hit) / (sum(idx_blks_hit) + sum(idx_blks_read))) * 100 
                    END as index_cache_hit_ratio
                FROM pg_statio_user_indexes
            """)
            
            index_cache_data = cursor.fetchone()
            
            cache_ratio = cache_data[2] if cache_data and cache_data[2] else 0
            index_cache_ratio = index_cache_data[2] if index_cache_data and index_cache_data[2] else 0
            
            result["cache_hit_ratio"] = {
                "table_cache_hit_ratio": round(cache_ratio, 2),
                "index_cache_hit_ratio": round(index_cache_ratio, 2),
                "heap_blocks_read": cache_data[0] if cache_data else 0,
                "heap_blocks_hit": cache_data[1] if cache_data else 0,
                "index_blocks_read": index_cache_data[0] if index_cache_data else 0,
                "index_blocks_hit": index_cache_data[1] if index_cache_data else 0
            }
            
            if cache_ratio < 90:
                warnings.append(f"Low cache hit ratio: {cache_ratio:.2f}% - consider increasing shared_buffers")
        
        # Slow queries
        if stat_type.lower() in ["slow_queries", "all"]:
            cursor.execute("""
                SELECT 
                    pid,
                    usename,
                    client_addr,
                    EXTRACT(EPOCH FROM (now() - query_start)) as duration_seconds,
                    state,
                    LEFT(query, 200) as query_preview,
                    wait_event_type,
                    wait_event
                FROM pg_stat_activity
                WHERE state = 'active'
                    AND pid != pg_backend_pid()
                    AND query_start < now() - interval '10 seconds'
                ORDER BY duration_seconds DESC
                LIMIT 20
            """)
            
            slow_queries = cursor.fetchall()
            
            result["slow_queries"] = [
                {
                    "pid": sq[0],
                    "user": sq[1],
                    "client_addr": str(sq[2]) if sq[2] else "local",
                    "duration_seconds": round(sq[3], 2) if sq[3] else 0,
                    "state": sq[4],
                    "query_preview": sq[5],
                    "wait_event_type": sq[6],
                    "wait_event": sq[7]
                }
                for sq in slow_queries
            ]
            
            if slow_queries:
                warnings.append(f"Found {len(slow_queries)} slow queries running longer than 10 seconds")
        
        # Locks
        if stat_type.lower() in ["locks", "all"]:
            cursor.execute("""
                SELECT 
                    l.locktype,
                    l.mode,
                    l.granted,
                    COUNT(*) as lock_count
                FROM pg_locks l
                GROUP BY l.locktype, l.mode, l.granted
                ORDER BY lock_count DESC
            """)
            
            locks = cursor.fetchall()
            
            cursor.execute("""
                SELECT 
                    blocked.pid AS blocked_pid,
                    blocked.usename AS blocked_user,
                    blocking.pid AS blocking_pid,
                    blocking.usename AS blocking_user,
                    LEFT(blocked.query, 200) AS blocked_query,
                    LEFT(blocking.query, 200) AS blocking_query
                FROM pg_stat_activity blocked
                JOIN pg_locks blocked_locks ON blocked.pid = blocked_locks.pid
                JOIN pg_locks blocking_locks ON (
                    blocked_locks.locktype = blocking_locks.locktype
                    AND blocked_locks.database IS NOT DISTINCT FROM blocking_locks.database
                    AND blocked_locks.relation IS NOT DISTINCT FROM blocking_locks.relation
                    AND blocked_locks.page IS NOT DISTINCT FROM blocking_locks.page
                    AND blocked_locks.tuple IS NOT DISTINCT FROM blocking_locks.tuple
                    AND blocked_locks.virtualxid IS NOT DISTINCT FROM blocking_locks.virtualxid
                    AND blocked_locks.transactionid IS NOT DISTINCT FROM blocking_locks.transactionid
                    AND blocked_locks.classid IS NOT DISTINCT FROM blocking_locks.classid
                    AND blocked_locks.objid IS NOT DISTINCT FROM blocking_locks.objid
                    AND blocked_locks.objsubid IS NOT DISTINCT FROM blocking_locks.objsubid
                    AND blocked_locks.pid != blocking_locks.pid
                )
                JOIN pg_stat_activity blocking ON blocking.pid = blocking_locks.pid
                WHERE NOT blocked_locks.granted
                    AND blocking_locks.granted
            """)
            
            blocking = cursor.fetchall()
            
            result["locks"] = {
                "lock_summary": [
                    {
                        "lock_type": lock[0],
                        "mode": lock[1],
                        "granted": lock[2],
                        "count": lock[3]
                    }
                    for lock in locks
                ],
                "blocking_queries": [
                    {
                        "blocked_pid": b[0],
                        "blocked_user": b[1],
                        "blocking_pid": b[2],
                        "blocking_user": b[3],
                        "blocked_query": b[4],
                        "blocking_query": b[5]
                    }
                    for b in blocking
                ]
            }
            
            if blocking:
                warnings.append(f"Found {len(blocking)} blocking queries that need attention")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return _format_result(
            status="success",
            operation="get_database_stats",
            duration_ms=duration_ms,
            result=result,
            message=f"Retrieved {stat_type} statistics successfully",
            warnings=warnings
        )
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return _format_result(
            status="error",
            operation="get_database_stats",
            duration_ms=duration_ms,
            message=f"Failed to get database statistics: {str(e)}"
        )
