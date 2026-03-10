import re
from typing import List, Any, Dict, Optional, Tuple


# Fields whose values are typically free-form text containing embedded data
FREE_TEXT_FIELDS = {
    "message", "raw_message", "body", "raw_body", "log",
    "msg", "text", "content", "description", "payload",
    "request_body", "response_body", "stacktrace", "exception",
}

# Separators that indicate a structural key-value pattern
_STRUCTURAL_SEP_PATTERN = re.compile(
    r'([\w.\-_]{1,60})\s*(?::|\s*=\s*>?|=\'|=")\s*$'
)

# Max length for a key_hint to be considered non-ambiguous
_MAX_KEY_HINT_LEN = 30


class PDNDetectors:
    @staticmethod
    def _is_surname(word: str, surn_ends: tuple) -> bool:
        return word.lower().endswith(surn_ends)

    @staticmethod
    def _is_patronymic(word: str, patron_ends: tuple) -> bool:
        return word.lower().endswith(patron_ends)

    @staticmethod
    def _is_initials(word: str) -> bool:
        # e.g., "И.О." or "И. О."
        return bool(re.match(r'^[A-ZА-ЯЁ]\.\s?[A-ZА-ЯЁ]\.$', word, re.IGNORECASE))

    @staticmethod
    def analyze_fio(text: str, surn_ends: tuple, patron_ends: tuple) -> List[str]:
        results = []
        # Pattern to extract 2 or 3 capitalized words
        fio_regex = re.compile(
            r'(?:^|\b|\s)([A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]+(?:\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]+|\s+[A-ZА-ЯЁ]\.\s?[A-ZА-ЯЁ]\.)(?:\s+[A-ZА-ЯЁ][a-zа-яёA-ZА-ЯЁ\-]+)?)(?=$|\b|\s|[!.,?])'
        )

        for match in fio_regex.finditer(text):
            candidate = match.group(1).strip()
            # Split candidate by spaces
            words = re.split(r'\s+', candidate)

            is_valid = False

            if len(words) == 3:
                w1, w2, w3 = words[0], words[1], words[2]
                
                # 1. Фамилия Имя Отчество
                if PDNDetectors._is_surname(w1, surn_ends) and PDNDetectors._is_patronymic(w3, patron_ends):
                    is_valid = True
                
                # 2. Отчество Фамилия Имя
                elif PDNDetectors._is_patronymic(w1, patron_ends) and PDNDetectors._is_surname(w2, surn_ends):
                    is_valid = True
                
                # 3. Имя Фамилия Отчество
                elif not PDNDetectors._is_surname(w1, surn_ends) and PDNDetectors._is_surname(w2, surn_ends) and PDNDetectors._is_patronymic(w3, patron_ends):
                    is_valid = True
            
            elif len(words) == 2:
                w1, w2 = words[0], words[1]
                
                # 4. Фамилия И.О.
                if PDNDetectors._is_surname(w1, surn_ends) and PDNDetectors._is_initials(w2):
                    is_valid = True
                    
                # И.О. Фамилия (rare but possible in text)
                elif PDNDetectors._is_initials(w1) and PDNDetectors._is_surname(w2, surn_ends):
                    is_valid = True

            if is_valid:
                results.append(candidate)

        return results

    @staticmethod
    def is_free_text_field(field_path: str) -> bool:
        """Check if the field is a known free-text field by its last path segment."""
        last_segment = field_path.rsplit(".", 1)[-1] if "." in field_path else field_path
        # Remove array indices like [0]
        last_segment = re.sub(r'\[\d+\]$', '', last_segment)
        return last_segment.lower() in FREE_TEXT_FIELDS

    @staticmethod
    def _extract_structural_key(text: str, match_start: int, match_end: int) -> Tuple[Optional[str], str]:
        """
        Look for a structural key pattern before the match in the text.
        
        Returns (key_hint, context_type):
          - ("phone", "structured_key") if found `phone: <match>` or `phone=<match>`
          - ("some long phrase here", "ambiguous") if key candidate is too long
          - (None, "free_text") if no structural key found
        """
        # Take up to 80 chars before the match for context analysis
        prefix_start = max(0, match_start - 80)
        prefix = text[prefix_start:match_start]

        # Try to find a key-separator pattern right before the match
        m = _STRUCTURAL_SEP_PATTERN.search(prefix)
        if m:
            key_candidate = m.group(1).strip()
            if len(key_candidate) == 0:
                return None, "free_text"
            # Check if key looks like a real key (no spaces, reasonable length)
            if len(key_candidate) <= _MAX_KEY_HINT_LEN and " " not in key_candidate:
                return key_candidate, "structured_key"
            else:
                return key_candidate[:_MAX_KEY_HINT_LEN], "ambiguous"

        return None, "free_text"

    @staticmethod
    def _check_nested_pdn(text_fragment: str, rules: List[Any]) -> bool:
        """
        Check if a text fragment contains PD (phone, email patterns).
        Used to sanitize prefix/suffix that might contain adjacent PD.
        """
        if not text_fragment:
            return False
        # Quick check with basic patterns for phone/email
        if re.search(r'(?:\+7|8)\s*[\(\-]?\s*\d{3}', text_fragment):
            return True
        if re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text_fragment):
            return True
        return False

    @classmethod
    def _classify_match(cls, text: str, match_value: str, match_start: int, match_end: int,
                        field_path: str, is_free_text: bool, rules: List[Any]) -> Dict:
        """
        Classify a single match with context information.

        Mode A (clean field): regex matches the whole value → structured_key, key_hint = last segment of field_path.
        Mode B (free text): regex matches part of text → analyze surrounding context.
        """
        # Mode A: the match covers most/all of the value (>= 90%)
        if not is_free_text or len(match_value) >= len(text.strip()) * 0.9:
            # Clean field — field_path itself is the context
            last_segment = field_path.rsplit(".", 1)[-1] if "." in field_path else field_path
            last_segment = re.sub(r'\[\d+\]$', '', last_segment)
            return {
                "context_type": "structured_key",
                "key_hint": last_segment,
                "prefix_raw": None,
                "suffix_raw": None,
            }

        # Mode B: free text analysis
        # Step 1: Look for a structural key before the match
        key_hint, context_type = cls._extract_structural_key(text, match_start, match_end)

        # Capture prefix/suffix context for logging (short fragments)
        prefix_raw = text[max(0, match_start - 50):match_start].strip() or None
        suffix_raw = text[match_end:match_end + 50].strip() or None

        # Step 3: Check if prefix/suffix themselves contain PD — if so, sanitize
        if prefix_raw and cls._check_nested_pdn(prefix_raw, rules):
            prefix_raw = None  # Don't store prefix that contains other PD
        if suffix_raw and cls._check_nested_pdn(suffix_raw, rules):
            suffix_raw = None

        return {
            "context_type": context_type,
            "key_hint": key_hint,
            "prefix_raw": prefix_raw,
            "suffix_raw": suffix_raw,
        }

    @classmethod
    def detect(cls, text: str, field_path: str, rules: List[Any],
               is_free_text: bool = False) -> List[Dict]:
        """
        Main detection method that applies regex rules and exclusions.
        
        Returns list of dicts:
        {
            "type": "phone",
            "value": "79265524242",
            "context_type": "structured_key" | "free_text" | "ambiguous",
            "key_hint": "client_phone" | None,
            "prefix_raw": "..." | None,
            "suffix_raw": "..." | None,
        }
        """
        surn_ends = ('ов', 'ова', 'ев', 'ева', 'ин', 'ина')
        patron_ends = ('ович', 'евич', 'овна', 'евна')

        # 1. Evaluate exclusions on field_path
        exclude_patterns = [r.value for r in rules if r.rule_type == 'exclude_pattern']
        for ep in exclude_patterns:
            try:
                if re.search(ep, field_path):
                    return []
            except re.error:
                pass

        exclude_keys = [r.value for r in rules if r.rule_type == 'exclude_key']
        path_parts = field_path.split('.')
        last_key = path_parts[-1] if path_parts else ''
        if last_key in exclude_keys:
            return []

        matches = []
        
        # 2. Extract by regex rules
        regex_rules = [r for r in rules if r.rule_type == 'regex']
        
        for r in regex_rules:
            if r.pdn_type == 'fio':
                # Handle FIO with intelligent analyzer
                # Load custom endings from rules if available
                custom_surn_ends = [rule.value for rule in rules if rule.rule_type in ('surn_end_cis', 'surn_end_world')]
                custom_patron_ends = [rule.value for rule in rules if rule.rule_type == 'patron_end']
                
                effective_surn_ends = tuple(custom_surn_ends) if custom_surn_ends else surn_ends
                effective_patron_ends = tuple(custom_patron_ends) if custom_patron_ends else patron_ends
                
                fio_matches = cls.analyze_fio(text, effective_surn_ends, effective_patron_ends)
                for fm in fio_matches:
                    # Find position of the FIO match in the text
                    pos = text.find(fm)
                    match_start = pos if pos >= 0 else 0
                    match_end = match_start + len(fm)
                    
                    ctx = cls._classify_match(text, fm, match_start, match_end,
                                              field_path, is_free_text, rules)
                    matches.append({
                        "type": "fio",
                        "value": fm,
                        **ctx,
                    })
                
            try:
                found = re.finditer(r.value, text)
                for match in found:
                    val = match.group(0).strip()
                    if val:
                        ctx = cls._classify_match(
                            text, val, match.start(), match.end(),
                            field_path, is_free_text, rules
                        )
                        matches.append({
                            "type": r.pdn_type,
                            "value": val,
                            **ctx,
                        })
            except re.error:
                continue

        # Deduplicate identical values of the same type
        unique_matches = []
        seen = set()
        for m in matches:
            identifier = f"{m['type']}:{m['value']}:{m['context_type']}:{m.get('key_hint', '')}"
            if identifier not in seen:
                seen.add(identifier)
                unique_matches.append(m)
        
        # 3. Filter out by prefix_exclude, suffix_exclude, invalid_def_code
        filtered_matches = []
        for m in unique_matches:
            m_type = m["type"]
            m_val = m["value"]
            
            type_rules = [r for r in rules if r.pdn_type == m_type or r.pdn_type == 'all']
            
            prefixes = [r.value for r in type_rules if r.rule_type == 'prefix_exclude']
            suffixes = [r.value for r in type_rules if r.rule_type == 'suffix_exclude']
            
            if any(m_val.startswith(p) for p in prefixes):
                continue
            if any(m_val.endswith(s) for s in suffixes):
                continue
            
            # invalid_def_code (for phones)
            if m_type == 'phone':
                invalid_defs = [r.value for r in type_rules if r.rule_type == 'invalid_def_code']
                clean_phone = re.sub(r'\D', '', m_val)
                # Russian phone: 11 digits: 79991234567. Def code is clean_phone[1:4]
                if len(clean_phone) == 11 and (clean_phone.startswith('7') or clean_phone.startswith('8')):
                    def_code = clean_phone[1:4]
                    if def_code in invalid_defs:
                        continue
                        
            filtered_matches.append(m)

        return filtered_matches
