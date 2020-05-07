class AvroParser():
    def __init__(self):
        self.init_data()
        self.PATTERNS = self.data['PATTERNS']
        self.NON_RULE_PATTERNS = [p for p in self.PATTERNS if 'rules' not in p]
        self.RULE_PATTERNS = [p for p in self.PATTERNS if 'rules' in p]

        self.VOWELS = self.data['VOWELS']
        self.CONSONANTS = self.data['CONSONANTS']
        self.CASESENSITIVES = self.data['CASESENSITIVES']
        self.DIGITS = self.data['DIGITS']

    def __del__(self):
        del self.data

    @classmethod
    def parse_text(cls, text):
        AvroParser = cls()
        return AvroParser.parse(text)

    def parse(self, text):
        """Parses input text, matches and replaces using avro library

        If a valid replacement is found, returns the replaced string. If
        no replacement is found, returns the input text.

        Usage:

        ::
        from avrolib import AvroParser
        avro = AvroParser
        avro.parse("ami banglay gan gai")

        """
        # Sanitize text case to meet phonetic comparison standards
        fixed_text = self._fix_string_case(self._utf(text))
        # prepare output list
        output = []
        # cursor end point
        cur_end = 0
        # iterate through input text
        for cur, i in enumerate(fixed_text):
            # Trap characters with unicode encoding errors
            try:
                i.encode('utf-8')
            except UnicodeDecodeError:
                uni_pass = False
            else:
                uni_pass = True
            # Default value for match
            match = {'matched': False}
            # Check cur is greater than or equals cur_end. If cursor is in
            # a position that has alread been processed/replaced, we don't
            # process anything at all
            if not uni_pass:
                cur_end = cur + 1
                output.append(i)
            elif cur >= cur_end and uni_pass:
                # Try looking in non rule self.PATTERNS with current string portion
                match = self._match_non_rule_patterns(fixed_text, cur)
                # Check if non rule self.PATTERNS have matched
                if match["matched"]:
                    output.append(match["replaced"])
                    cur_end = cur + len(match["found"])
                else:
                # if non rule self.PATTERNS have not matched, try rule self.PATTERNS
                    match = self._match_rule_patterns(fixed_text, cur)
                    # Check if rule self.PATTERNS have matched
                    if match["matched"]:
                        # Update cur_end as cursor + length of match found
                        cur_end =  cur + len(match["found"])
                        # Process its rules
                        replaced = self._process_rules(rules = match["rules"],
                                                fixed_text = fixed_text,
                                                cur = cur, cur_end = cur_end)
                        # If any rules match, output replacement from the
                        # rule, else output it's default top-level/default
                        # replacement
                        if replaced is not None:
                            # Rule has matched
                            output.append(replaced)
                        else:
                            # No rules have matched
                            # output common match
                            output.append(match["replaced"])

                # If none matched, append present cursor value
                if not match["matched"]:
                    cur_end = cur + 1
                    output.append(i)

        # End looping through input text and produce output
        return ''.join(output)

    def _match_non_rule_patterns(self, fixed_text, cur=0):
        """Matches given text at cursor position with non rule self.PATTERNS

        Returns a dictionary of three elements:

        - "matched" - Bool: depending on if match found
        - "found" - string/None: Value of matched pattern's 'find' key or none
        - "replaced": string Replaced string if match found else input string at
        cursor

        """
        pattern = self._exact_find_in_pattern(fixed_text, cur, self.NON_RULE_PATTERNS)
        if len(pattern) > 0:
            return {"matched": True, "found": pattern[0]['find'],
                    "replaced": pattern[0]['replace']}
        else:
            return {"matched": False, "found": None,
                    "replaced": fixed_text[cur]}

    def _match_rule_patterns(self, fixed_text, cur=0):
        """Matches given text at cursor position with rule self.PATTERNS

        Returns a dictionary of four elements:

        - "matched" - Bool: depending on if match found
        - "found" - string/None: Value of matched pattern's 'find' key or none
        - "replaced": string Replaced string if match found else input string at
        cursor
        - "rules": dict/None: A dict of rules or None if no match found

        """
        pattern = self._exact_find_in_pattern(fixed_text, cur, self.RULE_PATTERNS)
        # if len(pattern) == 1:
        if len(pattern) > 0:
            return {"matched": True, "found": pattern[0]['find'],
                    "replaced": pattern[0]['replace'], "rules": pattern[0]['rules']}
        else:
            return {"matched": False, "found": None,
                    "replaced": fixed_text[cur], "rules": None}

    def _exact_find_in_pattern(self, fixed_text, cur = 0, PATTERNS = None):
        """Returns pattern items that match given text, cur position and pattern"""
        if PATTERNS is None: PATTERNS = self.PATTERNS
        return [x for x in PATTERNS if (cur + len(x['find']) <= len(fixed_text))
                and x['find'] == fixed_text[cur:(cur + len(x['find']))]]

    def _process_rules(self, rules, fixed_text, cur = 0, cur_end = 1):
        """Process rules matched in pattern and returns suitable replacement

        If any rule's condition is satisfied, output the rules "replace",
        else output None

        """
        replaced = ''
        # iterate through rules
        for rule in rules:
            matched = False
            # iterate through matches
            for match in rule['matches']:
                matched = self._process_match(match, fixed_text, cur, cur_end)
                # Break out of loop if we dont' have a match. Here we are
                # trusting avrodict to have listed matches sequentially
                if not matched:
                    break
            # If a match is found, stop looping through rules any further
            if matched:
                replaced = rule['replace']
                break

        # if any match has been found return replace value
        if matched:
            return replaced
        else:
            return None

    def _process_match(self, match, fixed_text, cur, cur_end):
        """Processes a single match in rules"""
        # Set our tools
        # -- Initial/default value for replace
        replace = True
        # -- Set check cursor depending on match['type']
        if match['type'] == 'prefix':
            chk = cur - 1
        else:
            # suffix
            chk = cur_end
        # -- Set scope based on whether scope is negative
        if match['scope'].startswith('!'):
            scope = match['scope'][1:]
            negative = True
        else:
            scope = match['scope']
            negative = False

        # Let the matching begin
        # -- Punctuations
        if scope == 'punctuation':
            # Conditions: XORd with negative
            if (not ((chk < 0 and match['type'] == 'prefix') or
                    (chk >= len(fixed_text) and match['type'] == 'suffix') or
                    self._is_punctuation(fixed_text[chk]))
                ^ negative):
                replace = False
        elif scope == 'vowel':
            if (not (((chk >= 0 and match['type'] == 'prefix') or
                    (chk < len(fixed_text) and match['type'] == 'suffix'))
                    and self._is_vowel(fixed_text[chk]))
                ^ negative):
                replace =  False
        elif scope == 'consonant':
            if (not (((chk >= 0 and match['type'] == 'prefix') or
                    (chk < len(fixed_text) and match['type'] == 'suffix'))
                    and self._is_consonant(fixed_text[chk]))
                ^ negative):
                replace = False
        # -- Exacts
        elif scope == 'exact':
            # Prepare cursor for exact search
            if match['type'] == 'prefix':
                exact_start = cur - len(match['value'])
                exact_end = cur
            else:
                # suffix
                exact_start = cur_end
                exact_end = cur_end + len(match['value'])
            # Validate exact find.
            if not self._is_exact(match['value'], fixed_text, exact_start,
                                    exact_end, negative):
                replace = False
        # Return replace, which will be true if none of the checks above match
        return replace

    def _utf(self, text):
        # """Shortcut funnction for encoding given text with self._utf-8"""
        # try:
        #     output = unicode(text, encoding='self._utf-8')
        # except UnicodeDecodeError:
        #     output = text
        # except TypeError:
        #     output = text
        # return output
        return text

    def _count_vowels(self, text):
        """Count number of occurrences of self.VOWELS in a given string"""
        count = 0
        for char in text:
            if char.lower() in self.VOWELS:
                count += 1
        return count

    def _count_consonants(self, text):
        """Count number of occurrences of self.CONSONANTS in a given string"""
        count = 0
        for char in text:
            if char.lower() in self.CONSONANTS:
                count += 1
        return count

    def _is_vowel(self, char):
        """Check if given string is a vowel"""
        return char.lower() in self.VOWELS

    def _is_consonant(self, char):
        """Check if given string is a consonant"""
        return char.lower() in self.CONSONANTS

    def _is_number(self, char):
        """Check if given string is a number"""
        return char.lower() in self.DIGITS

    def _is_punctuation(self, char):
        """Check if given string is a punctuation"""
        return not (char.lower() in self.VOWELS or
                    char.lower() in self.CONSONANTS)

    def _is_case_sensitive(self, char):
        """Check if given string is case sensitive"""
        return char.lower() in self.CASESENSITIVES

    def _is_exact(self, needle, haystack, start, end, matchnot):
        """Check exact occurrence of needle in haystack"""
        return ((start >= 0 and end < len(haystack) and
                haystack[start:end] == needle) ^ matchnot)

    def _fix_string_case(self, text):
        """Converts case-insensitive characters to lower case

        Case-sensitive characters as defined in self.CASESENSITIVES
        retain their case, but others are converted to their lowercase
        equivalents. The result is a string with phonetic-compatible case
        which will the parser will understand without confusion.
        """
        fixed = []
        for char in text:
            if self._is_case_sensitive(char):
                fixed.append(char)
            else:
                fixed.append(char.lower())
        return ''.join(fixed)

    def init_data(self):
        self.data = {
            "PATTERNS": [
                {
                    "find": "bhl",
                    "replace": "ভ্ল"
                },
                {
                    "find": "psh",
                    "replace": "পশ"
                },
                {
                    "find": "bdh",
                    "replace": "ব্ধ"
                },
                {
                    "find": "bj",
                    "replace": "ব্জ"
                },
                {
                    "find": "bd",
                    "replace": "ব্দ"
                },
                {
                    "find": "bb",
                    "replace": "ব্ব"
                },
                {
                    "find": "bl",
                    "replace": "ব্ল"
                },
                {
                    "find": "bh",
                    "replace": "ভ"
                },
                {
                    "find": "vl",
                    "replace": "ভ্ল"
                },
                {
                    "find": "b",
                    "replace": "ব"
                },
                {
                    "find": "v",
                    "replace": "ভ"
                },
                {
                    "find": "cNG",
                    "replace": "চ্ঞ"
                },
                {
                    "find": "cch",
                    "replace": "চ্ছ"
                },
                {
                    "find": "cc",
                    "replace": "চ্চ"
                },
                {
                    "find": "ch",
                    "replace": "ছ"
                },
                {
                    "find": "c",
                    "replace": "চ"
                },
                {
                    "find": "dhn",
                    "replace": "ধ্ন"
                },
                {
                    "find": "dhm",
                    "replace": "ধ্ম"
                },
                {
                    "find": "dgh",
                    "replace": "দ্ঘ"
                },
                {
                    "find": "ddh",
                    "replace": "দ্ধ"
                },
                {
                    "find": "dbh",
                    "replace": "দ্ভ"
                },
                {
                    "find": "dv",
                    "replace": "দ্ভ"
                },
                {
                    "find": "dm",
                    "replace": "দ্ম"
                },
                {
                    "find": "DD",
                    "replace": "ড্ড"
                },
                {
                    "find": "Dh",
                    "replace": "ঢ"
                },
                {
                    "find": "dh",
                    "replace": "ধ"
                },
                {
                    "find": "dg",
                    "replace": "দ্গ"
                },
                {
                    "find": "dd",
                    "replace": "দ্দ"
                },
                {
                    "find": "D",
                    "replace": "ড"
                },
                {
                    "find": "d",
                    "replace": "দ"
                },
                {
                    "find": "...",
                    "replace": "..."
                },
                {
                    "find": ".`",
                    "replace": "."
                },
                {
                    "find": "..",
                    "replace": "।।"
                },
                {
                    "find": ".",
                    "replace": "।"
                },
                {
                    "find": "ghn",
                    "replace": "ঘ্ন"
                },
                {
                    "find": "Ghn",
                    "replace": "ঘ্ন"
                },
                {
                    "find": "gdh",
                    "replace": "গ্ধ"
                },
                {
                    "find": "Gdh",
                    "replace": "গ্ধ"
                },
                {
                    "find": "gN",
                    "replace": "গ্ণ"
                },
                {
                    "find": "GN",
                    "replace": "গ্ণ"
                },
                {
                    "find": "gn",
                    "replace": "গ্ন"
                },
                {
                    "find": "Gn",
                    "replace": "গ্ন"
                },
                {
                    "find": "gm",
                    "replace": "গ্ম"
                },
                {
                    "find": "Gm",
                    "replace": "গ্ম"
                },
                {
                    "find": "gl",
                    "replace": "গ্ল"
                },
                {
                    "find": "Gl",
                    "replace": "গ্ল"
                },
                {
                    "find": "gg",
                    "replace": "জ্ঞ"
                },
                {
                    "find": "GG",
                    "replace": "জ্ঞ"
                },
                {
                    "find": "Gg",
                    "replace": "জ্ঞ"
                },
                {
                    "find": "gG",
                    "replace": "জ্ঞ"
                },
                {
                    "find": "gh",
                    "replace": "ঘ"
                },
                {
                    "find": "Gh",
                    "replace": "ঘ"
                },
                {
                    "find": "g",
                    "replace": "গ"
                },
                {
                    "find": "G",
                    "replace": "গ"
                },
                {
                    "find": "hN",
                    "replace": "হ্ণ"
                },
                {
                    "find": "hn",
                    "replace": "হ্ন"
                },
                {
                    "find": "hm",
                    "replace": "হ্ম"
                },
                {
                    "find": "hl",
                    "replace": "হ্ল"
                },
                {
                    "find": "h",
                    "replace": "হ"
                },
                {
                    "find": "jjh",
                    "replace": "জ্ঝ"
                },
                {
                    "find": "jNG",
                    "replace": "জ্ঞ"
                },
                {
                    "find": "jh",
                    "replace": "ঝ"
                },
                {
                    "find": "jj",
                    "replace": "জ্জ"
                },
                {
                    "find": "j",
                    "replace": "জ"
                },
                {
                    "find": "J",
                    "replace": "জ"
                },
                {
                    "find": "kkhN",
                    "replace": "ক্ষ্ণ"
                },
                {
                    "find": "kShN",
                    "replace": "ক্ষ্ণ"
                },
                {
                    "find": "kkhm",
                    "replace": "ক্ষ্ম"
                },
                {
                    "find": "kShm",
                    "replace": "ক্ষ্ম"
                },
                {
                    "find": "kxN",
                    "replace": "ক্ষ্ণ"
                },
                {
                    "find": "kxm",
                    "replace": "ক্ষ্ম"
                },
                {
                    "find": "kkh",
                    "replace": "ক্ষ"
                },
                {
                    "find": "kSh",
                    "replace": "ক্ষ"
                },
                {
                    "find": "ksh",
                    "replace": "কশ"
                },
                {
                    "find": "kx",
                    "replace": "ক্ষ"
                },
                {
                    "find": "kk",
                    "replace": "ক্ক"
                },
                {
                    "find": "kT",
                    "replace": "ক্ট"
                },
                {
                    "find": "kt",
                    "replace": "ক্ত"
                },
                {
                    "find": "kl",
                    "replace": "ক্ল"
                },
                {
                    "find": "ks",
                    "replace": "ক্স"
                },
                {
                    "find": "kh",
                    "replace": "খ"
                },
                {
                    "find": "k",
                    "replace": "ক"
                },
                {
                    "find": "lbh",
                    "replace": "ল্ভ"
                },
                {
                    "find": "ldh",
                    "replace": "ল্ধ"
                },
                {
                    "find": "lkh",
                    "replace": "লখ"
                },
                {
                    "find": "lgh",
                    "replace": "লঘ"
                },
                {
                    "find": "lph",
                    "replace": "লফ"
                },
                {
                    "find": "lk",
                    "replace": "ল্ক"
                },
                {
                    "find": "lg",
                    "replace": "ল্গ"
                },
                {
                    "find": "lT",
                    "replace": "ল্ট"
                },
                {
                    "find": "lD",
                    "replace": "ল্ড"
                },
                {
                    "find": "lp",
                    "replace": "ল্প"
                },
                {
                    "find": "lv",
                    "replace": "ল্ভ"
                },
                {
                    "find": "lm",
                    "replace": "ল্ম"
                },
                {
                    "find": "ll",
                    "replace": "ল্ল"
                },
                {
                    "find": "lb",
                    "replace": "ল্ব"
                },
                {
                    "find": "l",
                    "replace": "ল"
                },
                {
                    "find": "mth",
                    "replace": "ম্থ"
                },
                {
                    "find": "mph",
                    "replace": "ম্ফ"
                },
                {
                    "find": "mbh",
                    "replace": "ম্ভ"
                },
                {
                    "find": "mpl",
                    "replace": "মপ্ল"
                },
                {
                    "find": "mn",
                    "replace": "ম্ন"
                },
                {
                    "find": "mp",
                    "replace": "ম্প"
                },
                {
                    "find": "mv",
                    "replace": "ম্ভ"
                },
                {
                    "find": "mm",
                    "replace": "ম্ম"
                },
                {
                    "find": "ml",
                    "replace": "ম্ল"
                },
                {
                    "find": "mb",
                    "replace": "ম্ব"
                },
                {
                    "find": "mf",
                    "replace": "ম্ফ"
                },
                {
                    "find": "m",
                    "replace": "ম"
                },
                {
                    "find": "0",
                    "replace": "০"
                },
                {
                    "find": "1",
                    "replace": "১"
                },
                {
                    "find": "2",
                    "replace": "২"
                },
                {
                    "find": "3",
                    "replace": "৩"
                },
                {
                    "find": "4",
                    "replace": "৪"
                },
                {
                    "find": "5",
                    "replace": "৫"
                },
                {
                    "find": "6",
                    "replace": "৬"
                },
                {
                    "find": "7",
                    "replace": "৭"
                },
                {
                    "find": "8",
                    "replace": "৮"
                },
                {
                    "find": "9",
                    "replace": "৯"
                },
                {
                    "find": "NgkSh",
                    "replace": "ঙ্ক্ষ"
                },
                {
                    "find": "Ngkkh",
                    "replace": "ঙ্ক্ষ"
                },
                {
                    "find": "NGch",
                    "replace": "ঞ্ছ"
                },
                {
                    "find": "Nggh",
                    "replace": "ঙ্ঘ"
                },
                {
                    "find": "Ngkh",
                    "replace": "ঙ্খ"
                },
                {
                    "find": "NGjh",
                    "replace": "ঞ্ঝ"
                },
                {
                    "find": "ngOU",
                    "replace": "ঙ্গৌ"
                },
                {
                    "find": "ngOI",
                    "replace": "ঙ্গৈ"
                },
                {
                    "find": "Ngkx",
                    "replace": "ঙ্ক্ষ"
                },
                {
                    "find": "NGc",
                    "replace": "ঞ্চ"
                },
                {
                    "find": "nch",
                    "replace": "ঞ্ছ"
                },
                {
                    "find": "njh",
                    "replace": "ঞ্ঝ"
                },
                {
                    "find": "ngh",
                    "replace": "ঙ্ঘ"
                },
                {
                    "find": "Ngk",
                    "replace": "ঙ্ক"
                },
                {
                    "find": "Ngx",
                    "replace": "ঙ্ষ"
                },
                {
                    "find": "Ngg",
                    "replace": "ঙ্গ"
                },
                {
                    "find": "Ngm",
                    "replace": "ঙ্ম"
                },
                {
                    "find": "NGj",
                    "replace": "ঞ্জ"
                },
                {
                    "find": "ndh",
                    "replace": "ন্ধ"
                },
                {
                    "find": "nTh",
                    "replace": "ন্ঠ"
                },
                {
                    "find": "NTh",
                    "replace": "ণ্ঠ"
                },
                {
                    "find": "nth",
                    "replace": "ন্থ"
                },
                {
                    "find": "nkh",
                    "replace": "ঙ্খ"
                },
                {
                    "find": "ngo",
                    "replace": "ঙ্গ"
                },
                {
                    "find": "nga",
                    "replace": "ঙ্গা"
                },
                {
                    "find": "ngi",
                    "replace": "ঙ্গি"
                },
                {
                    "find": "ngI",
                    "replace": "ঙ্গী"
                },
                {
                    "find": "ngu",
                    "replace": "ঙ্গু"
                },
                {
                    "find": "ngU",
                    "replace": "ঙ্গূ"
                },
                {
                    "find": "nge",
                    "replace": "ঙ্গে"
                },
                {
                    "find": "ngO",
                    "replace": "ঙ্গো"
                },
                {
                    "find": "NDh",
                    "replace": "ণ্ঢ"
                },
                {
                    "find": "nsh",
                    "replace": "নশ"
                },
                {
                    "find": "Ngr",
                    "replace": "ঙর"
                },
                {
                    "find": "NGr",
                    "replace": "ঞর"
                },
                {
                    "find": "ngr",
                    "replace": "ংর"
                },
                {
                    "find": "nj",
                    "replace": "ঞ্জ"
                },
                {
                    "find": "Ng",
                    "replace": "ঙ"
                },
                {
                    "find": "NG",
                    "replace": "ঞ"
                },
                {
                    "find": "nk",
                    "replace": "ঙ্ক"
                },
                {
                    "find": "ng",
                    "replace": "ং"
                },
                {
                    "find": "nn",
                    "replace": "ন্ন"
                },
                {
                    "find": "NN",
                    "replace": "ণ্ণ"
                },
                {
                    "find": "Nn",
                    "replace": "ণ্ন"
                },
                {
                    "find": "nm",
                    "replace": "ন্ম"
                },
                {
                    "find": "Nm",
                    "replace": "ণ্ম"
                },
                {
                    "find": "nd",
                    "replace": "ন্দ"
                },
                {
                    "find": "nT",
                    "replace": "ন্ট"
                },
                {
                    "find": "NT",
                    "replace": "ণ্ট"
                },
                {
                    "find": "nD",
                    "replace": "ন্ড"
                },
                {
                    "find": "ND",
                    "replace": "ণ্ড"
                },
                {
                    "find": "nt",
                    "replace": "ন্ত"
                },
                {
                    "find": "ns",
                    "replace": "ন্স"
                },
                {
                    "find": "nc",
                    "replace": "ঞ্চ"
                },
                {
                    "find": "n",
                    "replace": "ন"
                },
                {
                    "find": "N",
                    "replace": "ণ"
                },
                {
                    "find": "OI`",
                    "replace": "ৈ"
                },
                {
                    "find": "OU`",
                    "replace": "ৌ"
                },
                {
                    "find": "O`",
                    "replace": "ো"
                },
                {
                    "find": "OI",
                    "replace": "ৈ",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                }
                            ],
                            "replace": "ঐ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                }
                            ],
                            "replace": "ঐ"
                        }
                    ]
                },
                {
                    "find": "OU",
                    "replace": "ৌ",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                }
                            ],
                            "replace": "ঔ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                }
                            ],
                            "replace": "ঔ"
                        }
                    ]
                },
                {
                    "find": "O",
                    "replace": "ো",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                }
                            ],
                            "replace": "ও"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                }
                            ],
                            "replace": "ও"
                        }
                    ]
                },
                {
                    "find": "phl",
                    "replace": "ফ্ল"
                },
                {
                    "find": "pT",
                    "replace": "প্ট"
                },
                {
                    "find": "pt",
                    "replace": "প্ত"
                },
                {
                    "find": "pn",
                    "replace": "প্ন"
                },
                {
                    "find": "pp",
                    "replace": "প্প"
                },
                {
                    "find": "pl",
                    "replace": "প্ল"
                },
                {
                    "find": "ps",
                    "replace": "প্স"
                },
                {
                    "find": "ph",
                    "replace": "ফ"
                },
                {
                    "find": "fl",
                    "replace": "ফ্ল"
                },
                {
                    "find": "f",
                    "replace": "ফ"
                },
                {
                    "find": "p",
                    "replace": "প"
                },
                {
                    "find": "rri`",
                    "replace": "ৃ"
                },
                {
                    "find": "rri",
                    "replace": "ৃ",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                }
                            ],
                            "replace": "ঋ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                }
                            ],
                            "replace": "ঋ"
                        }
                    ]
                },
                {
                    "find": "rrZ",
                    "replace": "রর‍্য"
                },
                {
                    "find": "rry",
                    "replace": "রর‍্য"
                },
                {
                    "find": "rZ",
                    "replace": "র‍্য",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "consonant"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "r"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "y"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "w"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "x"
                                }
                            ],
                            "replace": "্র্য"
                        }
                    ]
                },
                {
                    "find": "ry",
                    "replace": "র‍্য",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "consonant"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "r"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "y"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "w"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "x"
                                }
                            ],
                            "replace": "্র্য"
                        }
                    ]
                },
                {
                    "find": "rr",
                    "replace": "রর",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!vowel"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "r"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!punctuation"
                                }
                            ],
                            "replace": "র্"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "consonant"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "r"
                                }
                            ],
                            "replace": "্রর"
                        }
                    ]
                },
                {
                    "find": "Rg",
                    "replace": "ড়্গ"
                },
                {
                    "find": "Rh",
                    "replace": "ঢ়"
                },
                {
                    "find": "R",
                    "replace": "ড়"
                },
                {
                    "find": "r",
                    "replace": "র",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "consonant"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "r"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "y"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "w"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "x"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "Z"
                                }
                            ],
                            "replace": "্র"
                        }
                    ]
                },
                {
                    "find": "shch",
                    "replace": "শ্ছ"
                },
                {
                    "find": "ShTh",
                    "replace": "ষ্ঠ"
                },
                {
                    "find": "Shph",
                    "replace": "ষ্ফ"
                },
                {
                    "find": "Sch",
                    "replace": "শ্ছ"
                },
                {
                    "find": "skl",
                    "replace": "স্ক্ল"
                },
                {
                    "find": "skh",
                    "replace": "স্খ"
                },
                {
                    "find": "sth",
                    "replace": "স্থ"
                },
                {
                    "find": "sph",
                    "replace": "স্ফ"
                },
                {
                    "find": "shc",
                    "replace": "শ্চ"
                },
                {
                    "find": "sht",
                    "replace": "শ্ত"
                },
                {
                    "find": "shn",
                    "replace": "শ্ন"
                },
                {
                    "find": "shm",
                    "replace": "শ্ম"
                },
                {
                    "find": "shl",
                    "replace": "শ্ল"
                },
                {
                    "find": "Shk",
                    "replace": "ষ্ক"
                },
                {
                    "find": "ShT",
                    "replace": "ষ্ট"
                },
                {
                    "find": "ShN",
                    "replace": "ষ্ণ"
                },
                {
                    "find": "Shp",
                    "replace": "ষ্প"
                },
                {
                    "find": "Shf",
                    "replace": "ষ্ফ"
                },
                {
                    "find": "Shm",
                    "replace": "ষ্ম"
                },
                {
                    "find": "spl",
                    "replace": "স্প্ল"
                },
                {
                    "find": "sk",
                    "replace": "স্ক"
                },
                {
                    "find": "Sc",
                    "replace": "শ্চ"
                },
                {
                    "find": "sT",
                    "replace": "স্ট"
                },
                {
                    "find": "st",
                    "replace": "স্ত"
                },
                {
                    "find": "sn",
                    "replace": "স্ন"
                },
                {
                    "find": "sp",
                    "replace": "স্প"
                },
                {
                    "find": "sf",
                    "replace": "স্ফ"
                },
                {
                    "find": "sm",
                    "replace": "স্ম"
                },
                {
                    "find": "sl",
                    "replace": "স্ল"
                },
                {
                    "find": "sh",
                    "replace": "শ"
                },
                {
                    "find": "Sc",
                    "replace": "শ্চ"
                },
                {
                    "find": "St",
                    "replace": "শ্ত"
                },
                {
                    "find": "Sn",
                    "replace": "শ্ন"
                },
                {
                    "find": "Sm",
                    "replace": "শ্ম"
                },
                {
                    "find": "Sl",
                    "replace": "শ্ল"
                },
                {
                    "find": "Sh",
                    "replace": "ষ"
                },
                {
                    "find": "s",
                    "replace": "স"
                },
                {
                    "find": "S",
                    "replace": "শ"
                },
                {
                    "find": "oo`",
                    "replace": "ু"
                },
                {
                    "find": "oo",
                    "replace": "ু",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "উ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "উ"
                        }
                    ]
                },
                {
                    "find": "o`",
                    "replace": ""
                },
                {
                    "find": "oZ",
                    "replace": "অ্য"
                },
                {
                    "find": "o",
                    "replace": "",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "vowel"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "o"
                                }
                            ],
                            "replace": "ও"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "vowel"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "exact",
                                    "value": "o"
                                }
                            ],
                            "replace": "অ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                }
                            ],
                            "replace": "অ"
                        }
                    ]
                },
                {
                    "find": "tth",
                    "replace": "ত্থ"
                },
                {
                    "find": "t``",
                    "replace": "ৎ"
                },
                {
                    "find": "TT",
                    "replace": "ট্ট"
                },
                {
                    "find": "Tm",
                    "replace": "ট্ম"
                },
                {
                    "find": "Th",
                    "replace": "ঠ"
                },
                {
                    "find": "tn",
                    "replace": "ত্ন"
                },
                {
                    "find": "tm",
                    "replace": "ত্ম"
                },
                {
                    "find": "th",
                    "replace": "থ"
                },
                {
                    "find": "tt",
                    "replace": "ত্ত"
                },
                {
                    "find": "T",
                    "replace": "ট"
                },
                {
                    "find": "t",
                    "replace": "ত"
                },
                {
                    "find": "aZ",
                    "replace": "অ্যা"
                },
                {
                    "find": "AZ",
                    "replace": "অ্যা"
                },
                {
                    "find": "a`",
                    "replace": "া"
                },
                {
                    "find": "A`",
                    "replace": "া"
                },
                {
                    "find": "a",
                    "replace": "া",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "আ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!exact",
                                    "value": "a"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "য়া"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "exact",
                                    "value": "a"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "আ"
                        }
                    ]
                },
                {
                    "find": "i`",
                    "replace": "ি"
                },
                {
                    "find": "i",
                    "replace": "ি",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ই"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ই"
                        }
                    ]
                },
                {
                    "find": "I`",
                    "replace": "ী"
                },
                {
                    "find": "I",
                    "replace": "ী",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ঈ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ঈ"
                        }
                    ]
                },
                {
                    "find": "u`",
                    "replace": "ু"
                },
                {
                    "find": "u",
                    "replace": "ু",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "উ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "উ"
                        }
                    ]
                },
                {
                    "find": "U`",
                    "replace": "ূ"
                },
                {
                    "find": "U",
                    "replace": "ূ",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ঊ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ঊ"
                        }
                    ]
                },
                {
                    "find": "ee`",
                    "replace": "ী"
                },
                {
                    "find": "ee",
                    "replace": "ী",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ঈ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "ঈ"
                        }
                    ]
                },
                {
                    "find": "e`",
                    "replace": "ে"
                },
                {
                    "find": "e",
                    "replace": "ে",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "এ"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "!exact",
                                    "value": "`"
                                }
                            ],
                            "replace": "এ"
                        }
                    ]
                },
                {
                    "find": "z",
                    "replace": "য"
                },
                {
                    "find": "Z",
                    "replace": "্য"
                },
                {
                    "find": "y",
                    "replace": "্য",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "!consonant"
                                },
                                {
                                    "type": "prefix",
                                    "scope": "!punctuation"
                                }
                            ],
                            "replace": "য়"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                }
                            ],
                            "replace": "ইয়"
                        }
                    ]
                },
                {
                    "find": "Y",
                    "replace": "য়"
                },
                {
                    "find": "q",
                    "replace": "ক"
                },
                {
                    "find": "w",
                    "replace": "ও",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                },
                                {
                                    "type": "suffix",
                                    "scope": "vowel"
                                }
                            ],
                            "replace": "ওয়"
                        },
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "consonant"
                                }
                            ],
                            "replace": "্ব"
                        }
                    ]
                },
                {
                    "find": "x",
                    "replace": "ক্স",
                    "rules": [
                        {
                            "matches": [
                                {
                                    "type": "prefix",
                                    "scope": "punctuation"
                                }
                            ],
                            "replace": "এক্স"
                        }
                    ]
                },
                {
                    "find": ":`",
                    "replace": ":"
                },
                {
                    "find": ":",
                    "replace": "ঃ"
                },
                {
                    "find": "^`",
                    "replace": "^"
                },
                {
                    "find": "^",
                    "replace": "ঁ"
                },
                {
                    "find": ",,",
                    "replace": "্‌"
                },
                {
                    "find": ",",
                    "replace": ","
                },
                {
                    "find": "$",
                    "replace": "৳"
                },
                {
                    "find": "`",
                    "replace": ""
                }
            ],
            "VOWELS": "aeiou",
            "CONSONANTS": "bcdfghjklmnpqrstvwxyz",
            "CASESENSITIVES": "oiudgjnrstyz",
            "DIGITS": "0123456789"
        }
