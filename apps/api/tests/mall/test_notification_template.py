from app.commerce.notify.templates import render


def test_template_interpolates_only_known_scalar_fields():
    result = render("订单 {{ order_id }}：{{status}} {{password}}", {
        "order_id": "order-1", "status": "PAID", "password": "must-not-render"})
    assert result == "订单 order-1：PAID "
    assert render("{{status}}", {"status": {"nested": "not rendered"}}) == ""
