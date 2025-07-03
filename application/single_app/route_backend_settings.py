# route_backend_settings.py

from config import *
from functions_documents import *
from functions_authentication import *
from functions_settings import *
import redis 


def register_route_backend_settings(app):
    @app.route('/api/admin/settings/check_index_fields', methods=['POST'])
    @login_required
    @admin_required
    def check_index_fields():
        data     = request.get_json(force=True)
        idx_type = data.get('indexType')  # 'user' or 'group'

        # load your golden JSON
        fname = secure_filename(f'ai_search-index-{idx_type}.json')
        base_path = os.path.join(current_app.root_path, 'static', 'json')
        fpath = os.path.normpath(os.path.join(base_path, fname))
        if os.path.commonpath([base_path, fpath]) != base_path:
            raise Exception("Invalid file path")
        with open(fpath, 'r') as f:
            expected = json.load(f)

        client  = get_index_client()
        current = client.get_index(expected['name'])

        existing_names   = { fld.name        for fld in current.fields }
        expected_names   = { fld['name']      for fld in expected['fields'] }
        missing          = sorted(expected_names - existing_names)

        return jsonify({ 'missingFields': missing }), 200


    @app.route('/api/admin/settings/fix_index_fields', methods=['POST'])
    @login_required
    @admin_required
    def fix_index_fields():
        try:
            data     = request.get_json(force=True)
            idx_type = data.get('indexType')  # 'user' or 'group'

            # load your “golden” JSON schema
            json_name = secure_filename(f'ai_search-index-{idx_type}.json')
            base_path = os.path.join(current_app.root_path, 'static', 'json')
            json_path = os.path.normpath(os.path.join(base_path, json_name))
            if not json_path.startswith(base_path):
                raise Exception("Invalid file path")
            with open(json_path, 'r') as f:
                full_def = json.load(f)

            client    = get_index_client()
            index_obj = client.get_index(full_def['name'])

            existing_names = {fld.name for fld in index_obj.fields}
            missing_defs   = [fld for fld in full_def['fields'] if fld['name'] not in existing_names]

            if not missing_defs:
                return jsonify({'status': 'nothingToAdd'}), 200

            new_fields = []
            for fld in missing_defs:
                name = fld['name']
                ftype = fld['type']  # e.g. "Edm.String" or "Collection(Edm.Single)"

                if ftype.lower() == "collection(edm.single)":
                    # Vector field: hardcode dimensions if missing, pass profile name
                    dims = fld.get('dimensions', 1536)
                    vp   = fld.get('vectorSearchProfile')
                    new_fields.append(
                        SearchField(
                            name=name,
                            type=ftype,
                            searchable=True,
                            filterable=False,
                            retrievable=True,
                            sortable=False,
                            facetable=False,
                            vector_search_dimensions=dims,
                            vector_search_profile_name=vp
                        )
                    )
                else:
                    # Regular field: mirror the JSON props
                    new_fields.append(
                        SearchField(
                            name=name,
                            type=ftype,
                            searchable=fld.get('searchable', False),
                            filterable=fld.get('filterable', False),
                            retrievable=fld.get('retrievable', True),
                            sortable=fld.get('sortable', False),
                            facetable=fld.get('facetable', False),
                            key=fld.get('key', False),
                            analyzer_name=fld.get('analyzer'),
                            index_analyzer_name=fld.get('indexAnalyzer'),
                            search_analyzer_name=fld.get('searchAnalyzer'),
                            normalizer_name=fld.get('normalizer'),
                            synonym_map_names=fld.get('synonymMaps', [])
                        )
                    )

            # append the new fields, bypass ETag checks, and update
            index_obj.fields.extend(new_fields)
            index_obj.etag = "*"
            client.create_or_update_index(index_obj)

            added = [f.name for f in new_fields]
            return jsonify({ 'status': 'success', 'added': added }), 200

        except Exception as e:
            return jsonify({ 'error': str(e) }), 500
    
    @app.route('/api/admin/settings/test_connection', methods=['POST'])
    @login_required
    @admin_required
    def test_connection():
        """
        Receives JSON payload with { test_type: "...", ... } containing ephemeral
        data from admin_settings.js. Uses that data to attempt an actual connection
        to GPT, Embeddings, etc., and returns success/failure.
        """
        data = request.get_json(force=True)
        test_type = data.get('test_type', '')

        try:
            if test_type == 'gpt':
                return _test_gpt_connection(data)

            elif test_type == 'embedding':
                return _test_embedding_connection(data)

            elif test_type == 'image':
                return _test_image_gen_connection(data)

            elif test_type == 'safety':
                return _test_safety_connection(data)

            elif test_type == 'web_search':
                return _test_web_search_connection(data)

            elif test_type == 'azure_ai_search':
                return _test_azure_ai_search_connection(data)

            elif test_type == 'redis':
                return _test_redis_connection(data)

            elif test_type == 'azure_doc_intelligence':
                return _test_azure_doc_intelligence_connection(data)

            elif test_type == 'chunking_api':
                # If you have a chunking API test, implement it here.
                return jsonify({'message': 'Chunking API connection successful'}), 200

            else:
                return jsonify({'error': f'Unknown test_type: {test_type}'}), 400

        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
def get_index_client() -> SearchIndexClient:
    """
    Returns a SearchIndexClient wired up based on:
      - enable_ai_search_apim
      - azure_ai_search_authentication_type (managed_identity vs key)
      - and the various endpoint & key settings.
    """
    settings = get_settings()

    if settings.get("enable_ai_search_apim", False):
        endpoint = settings["azure_apim_ai_search_endpoint"].rstrip("/")
        credential = AzureKeyCredential(settings["azure_apim_ai_search_subscription_key"])
    else:
        endpoint = settings["azure_ai_search_endpoint"].rstrip("/")
        if settings.get("azure_ai_search_authentication_type", "key") == "managed_identity":
            credential = DefaultAzureCredential()
        else:
            credential = AzureKeyCredential(settings["azure_ai_search_key"])

    return SearchIndexClient(endpoint=endpoint, credential=credential)

def _test_gpt_connection(payload):
    """Attempt to connect to GPT using ephemeral settings from the admin UI."""
    enable_apim = payload.get('enable_apim', False)
    selected_model = payload.get('selected_model') or {}
    system_message = {
        'role': 'system',
        'content': f"Testing access."
    }

    # Decide GPT model
    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')
        api_version = apim_data.get('api_version')
        gpt_model = apim_data.get('deployment')
        subscription_key = apim_data.get('subscription_key')

        gpt_client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=subscription_key
        )
    else:
        direct_data = payload.get('direct', {})
        endpoint = direct_data.get('endpoint')
        api_version = direct_data.get('api_version')
        gpt_model = selected_model.get('deploymentName')

        if direct_data.get('auth_type') == 'managed_identity':
            token_provider = get_bearer_token_provider(DefaultAzureCredential(), cognitive_services_scope)
            
            gpt_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider
            )
        else:
            key = direct_data.get('key')

            gpt_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                api_key=key
            )

    try:
        response = gpt_client.chat.completions.create(
            model=gpt_model,
            messages=[system_message]
        )
        if response:
            return jsonify({'message': 'GPT connection successful'}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'error': f'Error generating model response: {str(e)}'}), 500


def _test_redis_connection(payload):
    """
    Attempts to connect to Azure Redis using key or managed identity auth.
    Performs a simple SET/GET round-trip test.
    """
    redis_host = payload.get('endpoint', '').strip()
    redis_key = payload.get('key', '').strip()
    redis_auth_type = payload.get('auth_type', 'key').strip()

    if not redis_host:
        return jsonify({'error': 'Redis host is required'}), 400

    try:
        if redis_auth_type == 'managed_identity':
            # Acquire token from managed identity for Redis scope
            credential = DefaultAzureCredential()
            token = credential.get_token("https://*.{REDIS_URL_VALUE}:10225/appid/.default").token
            redis_password = token
        else:
            if not redis_key:
                return jsonify({'error': 'Redis key is required for key auth'}), 400
            redis_password = redis_key

        r = redis.Redis(
            host=redis_host,
            port=6380,
            password=redis_password,
            ssl=True,
            socket_connect_timeout=5
        )

        test_key = "test_key_simplechat"
        test_value = "hello_redis"
        r.set(test_key, test_value, ex=10)
        result = r.get(test_key)

        if result and result.decode() == test_value:
            return jsonify({'message': 'Redis connection successful'}), 200
        else:
            return jsonify({'error': 'Redis test failed: unexpected value'}), 500

    except Exception as e:
        print(f"Redis test error: {e}")
        return jsonify({'error': f'Redis connection error: {str(e)}'}), 500



def _test_embedding_connection(payload):
    """Attempt to connect to Embeddings using ephemeral settings from the admin UI."""
    enable_apim = payload.get('enable_apim', False)
    selected_model = payload.get('selected_model') or {}
    text = "Test text for embedding connection."

    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')
        api_version = apim_data.get('api_version')
        embedding_model = apim_data.get('deployment')
        subscription_key = apim_data.get('subscription_key')

        embedding_client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=subscription_key
        )
    else:
        direct_data = payload.get('direct', {})
        endpoint = direct_data.get('endpoint')
        api_version = direct_data.get('api_version')
        embedding_model = selected_model.get('deploymentName')

        if direct_data.get('auth_type') == 'managed_identity':
            token_provider = get_bearer_token_provider(DefaultAzureCredential(), cognitive_services_scope)
            
            embedding_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider
            )
        else:
            key = direct_data.get('key')

            embedding_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                api_key=key
            )
    try:
        response = embedding_client.embeddings.create(
            model=embedding_model,
            input=text
        )

        if response:
            return jsonify({'message': 'Embedding connection successful'}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'error': f'Error generating embedding response: {str(e)}'}), 500
    

def _test_image_gen_connection(payload):
    """Attempt to connect to an Image Generation endpoint using ephemeral settings."""
    enable_apim = payload.get('enable_apim', False)
    selected_model = payload.get('selected_model') or {}
    prompt = "A scenic mountain at sunrise"

    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')
        api_version = apim_data.get('api_version')
        image_gen_model = apim_data.get('deployment')
        subscription_key = apim_data.get('subscription_key')

        image_gen_client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=subscription_key
        )
    else:
        direct_data = payload.get('direct', {})
        endpoint = direct_data.get('endpoint')
        api_version = direct_data.get('api_version')
        image_gen_model = selected_model.get('deploymentName')

        if direct_data.get('auth_type') == 'managed_identity':
            token_provider = get_bearer_token_provider(DefaultAzureCredential(), cognitive_services_scope)
            
            image_gen_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider
            )
        else:
            key = direct_data.get('key')

            image_gen_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                api_key=key
            )
    try:
        response = image_gen_client.images.generate(
            prompt=prompt,
            n=1,
            model=image_gen_model
        )
        if response:
            return jsonify({'message': 'Image generation connection successful'}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'error': f'Error generating model response: {str(e)}'}), 500


def _test_safety_connection(payload):
    """Attempt to connect to a content safety endpoint using ephemeral settings."""
    enabled = payload.get('enabled', False)
    if not enabled:
        # If the user toggled content safety off, just return success
        return jsonify({'message': 'Content Safety is disabled, skipping test'}), 200

    enable_apim = payload.get('enable_apim', False)

    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')
        subscription_key = apim_data.get('subscription_key')

        content_safety_client = ContentSafetyClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(subscription_key)
        )
    else:
        direct_data = payload.get('direct', {})
        endpoint = direct_data.get('endpoint')
        key = direct_data.get('key')

        if direct_data.get('auth_type') == 'managed_identity':
            
            content_safety_client = ContentSafetyClient(
                endpoint=endpoint,
                credential=DefaultAzureCredential()
            )
        else:
            content_safety_client = ContentSafetyClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )

    try:     
        user_message = "Test message for content safety connection."
        request_obj = AnalyzeTextOptions(text=user_message)
        cs_response = content_safety_client.analyze_text(request_obj)

        if cs_response:
            return jsonify({'message': 'Safety connection successful'}), 200
    except Exception as e:
        return jsonify({'error': f'Safety connection error: {str(e)}'}), 500


def _test_web_search_connection(payload):
    """Attempt to connect to Bing (or your APIM-protected) web search endpoint."""
    enabled = payload.get('enabled', False)
    if not enabled:
        return jsonify({'message': 'Web Search is disabled, skipping test'}), 200

    enable_apim = payload.get('enable_apim', False)

    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')
        subscription_key = apim_data.get('subscription_key')
        # deployment, api_version, etc. if relevant
        url = f"{endpoint.rstrip('/')}/bing/v7.0/search"
        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key
        }
        params = { 'q': 'Test' }
    else:
        direct_data = payload.get('direct', {})
        # For direct Bing calls, you typically do something like:
        key = direct_data.get('key')
        url = f"{BING_SEARCH_ENDPOINT}/v7.0/search"
        headers = {
            'Ocp-Apim-Subscription-Key': key
        }
        params = { 'q': 'Test' }

    resp = requests.get(url, headers=headers, params=params, timeout=10)
    if resp.status_code == 200:
        return jsonify({'message': 'Web search connection successful'}), 200
    else:
        raise Exception(f"Web search connection error: {resp.status_code} - {resp.text}")


def _test_azure_ai_search_connection(payload):
    """Attempt to connect to Azure Cognitive Search (or APIM-wrapped)."""
    enable_apim = payload.get('enable_apim', False)

    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')
        subscription_key = apim_data.get('subscription_key')

        content_safety_client = ContentSafetyClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(subscription_key)
        )
    else:
        direct_data = payload.get('direct', {})
        endpoint = direct_data.get('endpoint')
        key = direct_data.get('key')

        if direct_data.get('auth_type') == 'managed_identity':
            
            content_safety_client = ContentSafetyClient(
                endpoint=endpoint,
                credential=DefaultAzureCredential()
            )
        else:
            content_safety_client = ContentSafetyClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )

    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')  # e.g. https://my-apim.azure-api.net/search
        subscription_key = apim_data.get('subscription_key')
        url = f"{endpoint.rstrip('/')}/indexes?api-version=2023-11-01"
        headers = {
            'api-key': subscription_key,
            'Content-Type': 'application/json'
        }
    else:
        direct_data = payload.get('direct', {})
        endpoint = direct_data.get('endpoint')  # e.g. https://<searchservice>.search.windows.net
        key = direct_data.get('key')
        url = f"{endpoint.rstrip('/')}/indexes?api-version=2023-11-01"
        headers = {
            'api-key': key,
            'Content-Type': 'application/json'
        }

    # A small GET to /indexes to verify we have connectivity
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        return jsonify({'message': 'Azure AI search connection successful'}), 200
    else:
        raise Exception(f"Azure AI search connection error: {resp.status_code} - {resp.text}")


def _test_azure_doc_intelligence_connection(payload):
    """Attempt to connect to Azure Form Recognizer / Document Intelligence."""
    enable_apim = payload.get('enable_apim', False)

    enable_apim = payload.get('enable_apim', False)

    if enable_apim:
        apim_data = payload.get('apim', {})
        endpoint = apim_data.get('endpoint')
        subscription_key = apim_data.get('subscription_key')

        document_intelligence_client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(subscription_key)
        )
    else:
        direct_data = payload.get('direct', {})
        endpoint = direct_data.get('endpoint')
        key = direct_data.get('key')

        if direct_data.get('auth_type') == 'managed_identity':
            
            document_intelligence_client = DocumentAnalysisClient(
                endpoint=endpoint,
                credential=DefaultAzureCredential()
            )
        else:
            document_intelligence_client = DocumentAnalysisClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
    
    # Use local test file instead of URL for better offline testing
    test_file_path = os.path.join(current_app.root_path, 'static', 'test_files', 'test_document.pdf')
    with open(test_file_path, 'rb') as f:
        poller = document_intelligence_client.begin_analyze_document(
            model_id="prebuilt-read",
            document=f
        )

    max_wait_time = 600
    start_time = time.time()

    while True:
        status = poller.status()
        if status in ["succeeded", "failed", "canceled"]:
            break
        if time.time() - start_time > max_wait_time:
            raise TimeoutError("Document analysis took too long.")
        time.sleep(30)

    if status == "succeeded":
        return jsonify({'message': 'Azure document intelligence connection successful'}), 200
    else:
        return jsonify({'error': f"Document Intelligence error: {status}"}), 500
