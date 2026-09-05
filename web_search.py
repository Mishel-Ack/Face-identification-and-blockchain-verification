"""
Web & Social Media Search Module.
Performs image-based visual search (Bing Visual Search / Google Cloud Vision WEB_DETECTION API)
and text search with face-embedding verification to discover matching web/social media content.
"""

import hashlib
import time
import os
import requests
import numpy as np
import cv2
from typing import List, Dict, Any

class WebSearchEngine:
    def __init__(self):
        # Default mock web index for fallback simulation if external queries return 0 results
        self.mock_social_posts = [
            {
                "platform": "Twitter / X",
                "post_id": "status_1784920491",
                "url": "https://x.com/tech_innovator/status/1784920491",
                "author": "@tech_innovator",
                "title": "Keynote Speaker at AI Summit 2026",
                "content": "Excited to present our newest breakthrough in neural visual search!",
                "timestamp": "2026-08-15T14:30:00Z",
                "image_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb",
                "associated_tags": ["AI", "Tech", "Keynote", "FaceRecognition"],
                "source": "demo_fallback_data"
            },
            {
                "platform": "LinkedIn",
                "post_id": "activity_92817401928",
                "url": "https://www.linkedin.com/posts/alex-dev_profile-update-activity-92817401928",
                "author": "Alex Dev",
                "title": "Updated Professional Profile Picture",
                "content": "New profile headshot for Q3 2026.",
                "timestamp": "2026-08-20T09:15:00Z",
                "image_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d",
                "associated_tags": ["Profile", "Headshot", "Developer"],
                "source": "demo_fallback_data"
            },
            {
                "platform": "Instagram",
                "post_id": "p_C9zL8xMvP2k",
                "url": "https://instagram.com/p/C9zL8xMvP2k",
                "author": "@cyber_security_daily",
                "title": "Identity & Security Verification Demo",
                "content": "Verifying public biometric signatures using decentralized identity protocols.",
                "timestamp": "2026-09-01T18:00:00Z",
                "image_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e",
                "associated_tags": ["Identity", "CyberSecurity", "Verification"],
                "source": "demo_fallback_data"
            }
        ]

    def search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes a real DuckDuckGo web/text search query.
        """
        results = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=5))
                for item in ddg_results:
                    domain = item["href"].split("//")[-1].split("/")[0]
                    results.append({
                        "platform": f"Web ({domain})",
                        "post_id": hashlib.md5(item["href"].encode()).hexdigest()[:12],
                        "url": item["href"],
                        "author": domain,
                        "title": item.get("title", ""),
                        "content": item.get("body", ""),
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "image_url": item["href"],
                        "associated_tags": ["WebResult", "LiveSearch"],
                        "source": "duckduckgo_text_search"
                    })
        except Exception as e:
            print(f"[WebSearchEngine] DuckDuckGo query warning: {e}")

        return results

    def search_bing_visual(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Performs real image-based reverse search via Bing Visual Search API if API key is provided.
        API Key read from environment variable `BING_VISUAL_SEARCH_KEY`.
        """
        api_key = os.getenv("BING_VISUAL_SEARCH_KEY")
        if not api_key or not os.path.exists(image_path):
            return []

        results = []
        try:
            endpoint = "https://api.bing.microsoft.com/v7.0/images/visualsearch"
            headers = {"Ocp-Apim-Subscription-Key": api_key}
            with open(image_path, "rb") as img_f:
                files = {"image": (os.path.basename(image_path), img_f, "image/jpeg")}
                response = requests.post(endpoint, headers=headers, files=files, timeout=8)

            if response.status_code == 200:
                data = response.json()
                tags = data.get("tags", [])
                for tag in tags:
                    for action in tag.get("actions", []):
                        if action.get("actionType") in ["VisualSearch", "PagesIncluding", "WebSearch"]:
                            for item in action.get("data", {}).get("value", []):
                                page_url = item.get("hostPageUrl") or item.get("contentUrl")
                                if page_url:
                                    domain = page_url.split("//")[-1].split("/")[0]
                                    results.append({
                                        "platform": f"Web Visual ({domain})",
                                        "post_id": hashlib.md5(page_url.encode()).hexdigest()[:12],
                                        "url": page_url,
                                        "author": item.get("hostPageDisplayUrl", domain),
                                        "title": item.get("name", "Visual Search Candidate"),
                                        "content": item.get("name", ""),
                                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                        "image_url": item.get("contentUrl", page_url),
                                        "associated_tags": ["BingVisualSearch", "ReverseImageMatch"],
                                        "source": "bing_visual_search_api"
                                    })
        except Exception as e:
            print(f"[WebSearchEngine] Bing Visual Search API warning: {e}")

        return results

    def search_google_vision_web(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Performs real image-based reverse search via Google Cloud Vision WEB_DETECTION API.
        Requires google-cloud-vision SDK and valid Application Default Credentials.
        """
        results = []
        try:
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            with open(image_path, "rb") as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = client.web_detection(image=image)
            web_detection = response.web_detection

            if web_detection.pages_with_matching_images:
                for page in web_detection.pages_with_matching_images[:5]:
                    domain = page.url.split("//")[-1].split("/")[0]
                    results.append({
                        "platform": f"Web Image Match ({domain})",
                        "post_id": hashlib.md5(page.url.encode()).hexdigest()[:12],
                        "url": page.url,
                        "author": domain,
                        "title": page.page_title or "Google Vision Match",
                        "content": page.page_title or "",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "image_url": page.full_matching_images[0].url if page.full_matching_images else page.url,
                        "associated_tags": ["GoogleCloudVision", "WebDetection"],
                        "source": "google_cloud_vision_api"
                    })
        except Exception as e:
            pass

        return results

    def find_matching_post(self, face_data: dict, query_keywords: str = "face identification profile social media", target_platforms: List[str] = None) -> Dict[str, Any]:
        """
        Searches web & social media sources given input face metadata & criteria.
        Integrates reverse image search APIs (Bing Visual Search / Google Cloud Vision) alongside keyword search,
        verifies candidate images against input face embeddings, and returns audit metadata.
        """
        search_results = []
        input_image_path = face_data.get("image_path", "")

        # 1. Reverse Image Search (Image-Based Visual Discovery)
        if input_image_path and os.path.exists(input_image_path):
            bing_visual_results = self.search_bing_visual(input_image_path)
            if bing_visual_results:
                search_results.extend(bing_visual_results)

            google_vision_results = self.search_google_vision_web(input_image_path)
            if google_vision_results:
                search_results.extend(google_vision_results)

        # 2. Keyword Text Search (DuckDuckGo Search)
        platform_str = " ".join(target_platforms) if target_platforms else "linkedin instagram twitter facebook"
        enhanced_query = f"{query_keywords} {platform_str}".strip()

        live_results = self.search_duckduckgo(enhanced_query)
        if live_results:
            search_results.extend(live_results)

        # 3. Add fallback indexed demo social posts if all live searches are empty
        is_demo_fallback = False
        if not search_results:
            search_results.extend(self.mock_social_posts)
            is_demo_fallback = True

        # 4. Candidate Scoring & Visual Face Embedding Verification
        query_terms = [t.lower() for t in query_keywords.split()]
        scored_matches = []

        input_embedding = None
        if face_data.get("faces") and len(face_data["faces"]) > 0:
            input_embedding = face_data["faces"][0]["encoding"].get("embedding")

        for item in search_results:
            title_text = item.get("title", "").lower()
            content_text = item.get("content", "").lower()
            
            # Text relevance score
            text_matches = sum(1 for term in query_terms if term in title_text or term in content_text)
            term_score = text_matches / len(query_terms) if query_terms else 0.5
            
            # Social platform boost
            url_lower = item.get("url", "").lower()
            is_social = any(p in url_lower for p in ["twitter.com", "x.com", "linkedin.com", "instagram.com", "facebook.com", "github.com", "youtube.com", "reddit.com"])
            platform_boost = 0.30 if is_social else 0.05
            
            # Real face visual similarity evaluation
            visual_sim = 0.50
            item_img_url = item.get("image_url", "")
            
            if input_embedding and len(input_embedding) > 0 and item_img_url:
                try:
                    img_bytes = None
                    if item_img_url.startswith("http://") or item_img_url.startswith("https://"):
                        resp = requests.get(item_img_url, timeout=4)
                        if resp.status_code == 200:
                            img_bytes = resp.content
                    elif os.path.exists(item_img_url):
                        with open(item_img_url, "rb") as f:
                            img_bytes = f.read()

                    if img_bytes:
                        np_arr = np.frombuffer(img_bytes, np.uint8)
                        cand_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                        if cand_img is not None:
                            from face_engine import FaceEngine
                            temp_engine = FaceEngine()
                            cand_bboxes, cand_crops = temp_engine.detect_faces_from_array(cand_img) if hasattr(temp_engine, 'detect_faces_from_array') else ([(0, 0, cand_img.shape[1], cand_img.shape[0])], [cand_img])
                            if cand_crops:
                                cand_encoding = temp_engine.encode_face(cand_crops[0])
                                input_enc_dict = face_data["faces"][0]["encoding"]
                                visual_sim = temp_engine.compute_similarity(input_enc_dict, cand_encoding)
                except Exception:
                    visual_sim = 0.40

            # Compute Candidate Relevance Score (Text + Platform + Real Visual Similarity)
            candidate_relevance_score = min(0.99, max(0.20, round(0.30 * term_score + platform_boost + 0.50 * visual_sim, 4)))
            
            item["visual_verified"] = visual_sim >= 0.60
            item["computed_visual_sim"] = visual_sim
            item["candidate_relevance_score"] = candidate_relevance_score
            scored_matches.append((candidate_relevance_score, item))

        # Sort matches by candidate relevance score
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        top_relevance, selected_match = scored_matches[0]

        # Compute canonical content fingerprint digest
        from fingerprint_hasher import create_canonical_record, compute_bytes32_hash
        
        canonical_record = create_canonical_record(
            post_url=selected_match['url'],
            post_text=selected_match.get('title', '') + ' - ' + selected_match.get('content', ''),
            image_sha256=face_data.get("image_hash", ""),
            source=selected_match.get('author', 'web_search'),
            discovered_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        content_hash = compute_bytes32_hash(canonical_record)

        matched_post = {
            "matched": True,
            "candidate_relevance_score": top_relevance,
            "match_confidence": top_relevance,  # retained for backward compatibility
            "is_demo_fallback": is_demo_fallback,
            "search_source": selected_match.get("source", "unknown"),
            "post_metadata": selected_match,
            "face_input_hash": face_data.get("image_hash"),
            "canonical_record": canonical_record,
            "content_fingerprint": content_hash,
            "discovered_at": canonical_record["discovered_at"]
        }

        return matched_post

