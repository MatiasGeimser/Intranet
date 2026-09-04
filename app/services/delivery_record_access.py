DELIVERY_RECORDS_ONLY_EMAIL = "rodrigo.torres@braincorp.cl"


def is_delivery_records_only_user(user) -> bool:
    """Identifica la cuenta restringida exclusivamente a Actas de Entrega."""
    return bool(
        user
        and user.email
        and user.email.strip().casefold() == DELIVERY_RECORDS_ONLY_EMAIL
    )
