import requests
import os
import urllib.parse
import re

class ActionNetwork():
    UUID_REGEX = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

    def __init__(self, key=None):
        self.base_url = "https://actionnetwork.org/api/v2/"
        self.api_key = key if key else os.environ.get("ACTION_NETWORK_API")
        if not self.api_key:
            raise "API Key not provided"
    
    def get(self, resource, id):
        resource_url = urllib.parse.urljoin(self.base_url, resource)
        url = f"{resource_url}/{id}"
        return self._extract_ids(self._get(url).json())

    def get_page(self, resource, page=1, **kwargs):
        url = urllib.parse.urljoin(self.base_url, resource)
        params = kwargs['params'] if kwargs.get('params') else {}
        params['page'] = page
        kwargs['params'] = params
        res = self._get(url, **kwargs)
        if res.status_code == 200:
            return res.json()["_embedded"][self._get_resource_slug(resource)]
    
    def get_all(self, resource, **kwargs):
        result_page = [None]
        results = []
        url = urllib.parse.urljoin(self.base_url, resource)
        slug = self._get_resource_slug(resource)
        while len(result_page) > 0:
            res = self._get(url, **kwargs)
            if res.status_code != 200:
                # TODO: Throw error
                break
            page = res.json()
            result_page = page["_embedded"][slug]
            if not page["_links"].get("next"):
                break
            url = page["_links"]["next"]["href"]
            results.extend(result_page)
        
        return [self._extract_ids(result) for result in results]
    
    def _request(self, method, url, **kwargs):
        headers = kwargs['headers'] if kwargs.get('headers') else {}
        headers["OSDI-API-Token"] = self.api_key
        headers["Content-Type"] = "Application/JSON"
        kwargs['headers'] = headers
        return requests.request(method, url, **kwargs)

    def _get(self, url, **kwargs):
        return self._request("GET", url, **kwargs)
    
    def _delete(self, url, **kwargs):
        return self._request("DELETE", url, **kwargs)
    
    def post(self, relative_url, **kwargs):
        url = urllib.parse.urljoin(self.base_url, relative_url)
        return self._request("POST", url, **kwargs)
    
    def put(self, relative_url, **kwargs):
        url = urllib.parse.urljoin(self.base_url, relative_url)
        return self._request("PUT", url, **kwargs)
    
    def delete(self, relative_url, **kwargs):
        url = urllib.parse.urljoin(self.base_url, relative_url)
        return self._delete(url, **kwargs)
    
    def _get_resource_slug(self, resource):
        if "/" in resource:
            slug = resource.split('/')[-1]
        else:
            slug = resource
        prefix = "osdi" if self._is_osdi(slug) else "action_network"
        return f"{prefix}:{slug}"
    
    def _is_osdi(self, resource_slug):
        return not resource_slug in ['custom_fields', 'campaigns', 'event_campaigns']
    
    def _extract_ids(self, resource):
        for key in resource["_links"]:
            prefix = key.split(":")[-1]
            if prefix in ["person", "tag", "event_campaign", "event", "petition", "form"] or key == "self":
                uuids = self.UUID_REGEX.findall(resource["_links"][key]["href"])
                id_key = f"{prefix}_id" if key != "self" else "id"
                resource[id_key] = uuids[-1]
        return resource

if __name__ == "__main__":
    pass