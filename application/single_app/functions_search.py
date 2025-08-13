# functions_search.py

from config import *
from functions_content import *
import logging
import traceback
import os

# Configure logger for container debugging with environment variable support
logger = logging.getLogger(__name__)

# Get log level from environment variable, default to INFO for production
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Map string to logging level
level_mapping = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Set the log level, fallback to INFO if invalid level provided
log_level = level_mapping.get(LOG_LEVEL, logging.INFO)
logger.setLevel(log_level)

# Create console handler with formatting
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Also control other noisy loggers when not in DEBUG mode
if LOG_LEVEL != 'DEBUG':
    # Reduce noise from Azure SDK and other third-party libraries
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('msal').setLevel(logging.WARNING)

# Log the current log level for visibility
logger.info(f"functions_search logging initialized with level: {LOG_LEVEL}")

def hybrid_search(query, user_id, document_id=None, top_n=12, doc_scope="all", active_group_id=None):
    """
    Hybrid search that queries the user doc index or the group doc index
    depending on doc type.
    If document_id is None, we just search the user index for the user's docs
    OR you could unify that logic further (maybe search both).
    """
    # DEBUG: Log entry to function with all parameters
    logger.info("hybrid_search called with parameters:")
    logger.info(f"  query: '{query}'")
    logger.info(f"  user_id: '{user_id}'")
    logger.info(f"  document_id: '{document_id}'")
    logger.info(f"  top_n: {top_n}")
    logger.info(f"  doc_scope: '{doc_scope}'")
    logger.info(f"  active_group_id: '{active_group_id}'")
    
    try:
        # DEBUG: Attempting to generate embedding
        logger.debug(f"Attempting to generate embedding for query: '{query}'")
        query_embedding = generate_embedding(query)
        
        # DEBUG: Check embedding result
        if query_embedding is None:
            logger.error(f"generate_embedding returned None for query: '{query}'")
            return None
        else:
            logger.debug(f"Successfully generated embedding - type: {type(query_embedding)}, length: {len(query_embedding) if hasattr(query_embedding, '__len__') else 'N/A'}")
    
    except Exception as e:
        logger.error(f"Exception during embedding generation: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None
    
    try:
        # DEBUG: Attempting to get search clients from CLIENTS dictionary
        logger.debug("Attempting to retrieve search clients from CLIENTS dictionary")
        logger.debug(f"Available CLIENTS keys: {list(CLIENTS.keys()) if 'CLIENTS' in globals() else 'CLIENTS not found in globals'}")
        
        search_client_user = CLIENTS['search_client_user']
        search_client_group = CLIENTS['search_client_group']
        
        logger.debug(f"Successfully retrieved search clients - user: {type(search_client_user)}, group: {type(search_client_group)}")
        
    except KeyError as e:
        logger.error(f"KeyError accessing search clients: {str(e)}")
        logger.error(f"Available CLIENTS keys: {list(CLIENTS.keys()) if 'CLIENTS' in globals() else 'CLIENTS not found'}")
        return None
    except Exception as e:
        logger.error(f"Exception accessing search clients: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

    try:
        # DEBUG: Creating vector query
        logger.debug(f"Creating VectorizedQuery with embedding length: {len(query_embedding) if hasattr(query_embedding, '__len__') else 'unknown'}")
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_n,
            fields="embedding"
        )
        logger.debug(f"Successfully created VectorizedQuery: {type(vector_query)}")
        
    except Exception as e:
        logger.error(f"Exception creating VectorizedQuery: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

    # DEBUG: Entering document scope logic
    logger.debug(f"Processing doc_scope: '{doc_scope}'")
    
    if doc_scope == "all":
        logger.debug(f"Processing 'all' scope - document_id: '{document_id}', active_group_id: '{active_group_id}'")
        
        if document_id:
            logger.debug(f"Searching with specific document_id: '{document_id}'")
            
            try:
                # DEBUG: User search with document_id
                logger.debug(f"Performing user search with filter: user_id eq '{user_id}' and document_id eq '{document_id}'")
                user_results = search_client_user.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"user_id eq '{user_id}' and document_id eq '{document_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-user-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "user_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"User search completed successfully - result type: {type(user_results)}")
                
            except Exception as e:
                logger.error(f"Exception during user search (with document_id): {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None

            try:
                # DEBUG: Group search with document_id
                logger.debug(f"Performing group search with filter: group_id eq '{active_group_id}' and document_id eq '{document_id}'")
                group_results = search_client_group.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"group_id eq '{active_group_id}' and document_id eq '{document_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-group-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "group_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"Group search completed successfully - result type: {type(group_results)}")
                
            except Exception as e:
                logger.error(f"Exception during group search (with document_id): {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
        else:
            logger.debug("Searching without document_id (all documents)")
            
            try:
                # DEBUG: User search without document_id
                logger.debug(f"Performing user search with filter: user_id eq '{user_id}'")
                user_results = search_client_user.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"user_id eq '{user_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-user-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "user_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"User search completed successfully - result type: {type(user_results)}")
                
            except Exception as e:
                logger.error(f"Exception during user search (without document_id): {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None

            try:
                # DEBUG: Group search without document_id
                logger.debug(f"Performing group search with filter: group_id eq '{active_group_id}'")
                group_results = search_client_group.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"group_id eq '{active_group_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-group-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "group_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"Group search completed successfully - result type: {type(group_results)}")
                
            except Exception as e:
                logger.error(f"Exception during group search (without document_id): {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None

        try:
            # DEBUG: Extract and combine results
            logger.debug("Extracting search results from user and group searches")
            user_results_final = extract_search_results(user_results, top_n)
            logger.debug(f"User results extracted - count: {len(user_results_final) if user_results_final else 0}")
            
            group_results_final = extract_search_results(group_results, top_n)
            logger.debug(f"Group results extracted - count: {len(group_results_final) if group_results_final else 0}")
            
            results = user_results_final + group_results_final
            logger.debug(f"Combined results - total count: {len(results) if results else 0}")
            
        except Exception as e:
            logger.error(f"Exception during result extraction for 'all' scope: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    elif doc_scope == "personal":
        logger.debug("Processing 'personal' scope")
        
        try:
            if document_id:
                logger.debug(f"Personal search with document_id: '{document_id}'")
                user_results = search_client_user.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"user_id eq '{user_id}' and document_id eq '{document_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-user-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "user_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"Personal search (with document_id) completed successfully")
                results = extract_search_results(user_results, top_n)
            else:
                logger.debug("Personal search for all user documents")
                user_results = search_client_user.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"user_id eq '{user_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-user-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "user_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"Personal search (all documents) completed successfully")
                results = extract_search_results(user_results, top_n)
                
        except Exception as e:
            logger.error(f"Exception during personal search: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    elif doc_scope == "group":
        logger.debug("Processing 'group' scope")
        
        try:
            if document_id:
                logger.debug(f"Group search with document_id: '{document_id}'")
                group_results = search_client_group.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"group_id eq '{active_group_id}' and document_id eq '{document_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-group-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "group_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"Group search (with document_id) completed successfully")
                results = extract_search_results(group_results, top_n)
            else:
                logger.debug("Group search for all group documents")
                group_results = search_client_group.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=f"group_id eq '{active_group_id}'",
                    query_type="semantic",
                    semantic_configuration_name="nexus-group-index-semantic-configuration",
                    query_caption="extractive",
                    query_answer="extractive",
                    select=["id", "chunk_text", "chunk_id", "file_name", "group_id", "version", "chunk_sequence", "upload_date", "document_classification", "page_number", "author", "chunk_keywords", "title", "chunk_summary"]
                )
                logger.debug(f"Group search (all documents) completed successfully")
                results = extract_search_results(group_results, top_n)
                
        except Exception as e:
            logger.error(f"Exception during group search: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    else:
        logger.error(f"Unknown doc_scope: '{doc_scope}'. Valid values are 'all', 'personal', 'group'")
        return None
    
    try:
        # DEBUG: Final result processing
        logger.debug(f"Sorting and limiting results to top {top_n}")
        results = sorted(results, key=lambda x: x['score'], reverse=True)[:top_n]
        logger.info(f"hybrid_search completed successfully - returning {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Exception during final result processing: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def extract_search_results(paged_results, top_n):
    """
    Extract search results from paged results with comprehensive debugging
    """
    logger.debug(f"extract_search_results called with top_n: {top_n}")
    logger.debug(f"paged_results type: {type(paged_results)}")
    
    try:
        extracted = []
        result_count = 0
        
        for i, r in enumerate(paged_results):
            if i >= top_n:
                logger.debug(f"Reached top_n limit ({top_n}), breaking loop")
                break
                
            try:
                # DEBUG: Log each result processing
                logger.debug(f"Processing result {i+1}: id={r.get('id', 'N/A')}, file_name={r.get('file_name', 'N/A')}")
                
                extracted.append({
                    "id": r["id"],
                    "chunk_text": r["chunk_text"],
                    "chunk_id": r["chunk_id"],
                    "file_name": r["file_name"],
                    "group_id": r.get("group_id"),
                    "version": r["version"],
                    "chunk_sequence": r["chunk_sequence"],
                    "upload_date": r["upload_date"],
                    "document_classification": r["document_classification"],
                    "page_number": r["page_number"],
                    "author": r["author"],
                    "chunk_keywords": r["chunk_keywords"],
                    "title": r["title"],
                    "chunk_summary": r["chunk_summary"],
                    "score": r["@search.score"]
                })
                result_count += 1
                
            except KeyError as e:
                logger.error(f"KeyError processing result {i+1}: missing key {str(e)}")
                logger.error(f"Available keys in result: {list(r.keys()) if hasattr(r, 'keys') else 'N/A'}")
                continue
            except Exception as e:
                logger.error(f"Exception processing result {i+1}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        logger.debug(f"extract_search_results completed - extracted {result_count} results")
        return extracted
        
    except Exception as e:
        logger.error(f"Exception in extract_search_results: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []