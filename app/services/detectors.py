import re
from typing import List, Any, Dict

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
                
                # 3. Имя Фамилия Отчество (wait, usually if w3 is patronymic, w2 could be surname. But Russian is flexible)
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

    @classmethod
    def detect(cls, text: str, field_path: str, rules: List[Any]) -> List[Dict[str, str]]:
        """
        Main detection method that applies regex rules and exclusions.
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
                fio_matches = cls.analyze_fio(text, surn_ends, patron_ends)
                for fm in fio_matches:
                    matches.append({"type": "fio", "value": fm})
                # We can also add standard regex match for FIO if defined
                
            try:
                found = re.finditer(r.value, text)
                for match in found:
                    val = match.group(0).strip()
                    if val:
                        matches.append({"type": r.pdn_type, "value": val})
            except re.error:
                continue

        # Deduplicate identical values of the same type
        unique_matches = []
        seen = set()
        for m in matches:
            identifier = f"{m['type']}:{m['value']}"
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
