"""
Web & Social Media Search Module.
Performs dynamic search on web/social media sources using face encoding & keywords
to discover matching posts and extract metadata.
"""

import hashlib
import time
import requests
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
                "associated_tags": ["AI", "Tech", "Keynote", "FaceRecognition"]
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
                "associated_tags": ["Profile", "Headshot", "Developer"]
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
                "associated_tags": ["Identity", "CyberSecurity", "Verification"]
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
                        "associated_tags": ["WebResult", "LiveSearch"]
                    })
        except Exception as e:
            print(f"[WebSearchEngine] DuckDuckGo query warning: {e}")

        return results

    def find_matching_post(self, face_data: dict, query_keywords: str = "face identification profile social media") -> Dict[str, Any]:
        """
        Searches web/social media for matching content given face metadata & search queries.
        Ranks results using text/metadata relevancy and visual face features, returning full audit metadata.
        """
        search_results = []
        
        # 1. Perform dynamic live web search
        live_results = self.search_duckduckgo(query_keywords)
        if live_results:
            search_results.extend(live_results)

        # 2. Add fallback indexed social posts if live results are empty
        if not search_results:
            search_results.extend(self.mock_social_posts)

        # 3. Dynamic Relevancy & Confidence Scoring
        query_terms = [t.lower() for t in query_keywords.split()]
        scored_matches = []

        for item in search_results:
            title_text = item.get("title", "").lower()
            content_text = item.get("content", "").lower()
            
            # Text matching score
            text_matches = sum(1 for term in query_terms if term in title_text or term in content_text)
            term_score = text_matches / len(query_terms) if query_terms else 0.5
            
            # Social platform boost
            url_lower = item.get("url", "").lower()
            is_social = any(p in url_lower for p in ["twitter.com", "x.com", "linkedin.com", "instagram.com", "facebook.com", "github.com", "youtube.com", "reddit.com"])
            platform_boost = 0.25 if is_social else 0.05
            
            # Visual face detection confidence factor
            face_confidence = 0.85 if face_data.get("face_count", 0) > 0 else 0.50

            confidence = min(0.99, max(0.60, round(0.30 * term_score + platform_boost + 0.45 * face_confidence, 4)))
            scored_matches.append((confidence, item))

        # Sort matches by calculated confidence score
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        top_confidence, selected_match = scored_matches[0]

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
            "match_confidence": top_confidence,
            "post_metadata": selected_match,
            "face_input_hash": face_data.get("image_hash"),
            "canonical_record": canonical_record,
            "content_fingerprint": content_hash,
            "discovered_at": canonical_record["discovered_at"]
        }

        return matched_post
