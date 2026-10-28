from datetime import date, datetime


class validators:
    def __init__(self, request_id):
        self.request_id = request_id

    def required_fields(self, state):
        fields = ["Name", "DOB", "ID_number", "ID_expiry"]
        return [field for field in fields if state.get(field) is None or not str(state.get(field)).strip()]

    def validate_date_format(self, state):
        errors = []
        for field in ["DOB", "ID_expiry"]:
            try:
                datetime.strptime(str(state.get(field)), "%Y-%m-%d")
            except (ValueError, TypeError):
                errors.append(field)
        return errors

    def validate_date_logic(self, state):
        errors = []
        for field in ["DOB", "ID_expiry"]:
            try:
                parsed_date = datetime.strptime(str(state.get(field)), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            if field == "DOB" and parsed_date > date.today():
                errors.append("DOB cannot be in the future")
            if field == "ID_expiry" and parsed_date < date.today():
                errors.append("Document has expired")
        return errors

    def validate_ocr_confidence(self, state):
        confidence = state.get("ocr_confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            return ["ocr_confidence"]
        return ["ocr_confidence"] if confidence < 0.60 else []

    def run_all_checks(self, state):
        errors = [
            *self.required_fields(state),
            *self.validate_date_format(state),
            *self.validate_date_logic(state),
            *self.validate_ocr_confidence(state),
        ]
        return list(dict.fromkeys(errors))
