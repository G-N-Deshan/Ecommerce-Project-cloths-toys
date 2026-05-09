from decimal import Decimal

from myapp.models import Cloths, NewArrivals, Offers, ProductVariant, Toy

DEFAULT_SIZES = "S, M, L, XL"
DEFAULT_COLORS = "Red, Blue, Black"


def apply_defaults(obj):
    changed = False
    if hasattr(obj, "sizes_available") and not (obj.sizes_available or "").strip():
        obj.sizes_available = DEFAULT_SIZES
        changed = True
    if hasattr(obj, "colors_available") and not (obj.colors_available or "").strip():
        obj.colors_available = DEFAULT_COLORS
        changed = True
    if changed:
        obj.save()


cloth = Cloths.objects.filter(id=10).first() or Cloths.objects.first()
if cloth:
    apply_defaults(cloth)
    if not cloth.variants.exists():
        ProductVariant.objects.create(
            cloth=cloth,
            size="S",
            color="Red",
            color_code="#ef4444",
            extra_price=Decimal("0.00"),
            stock=10,
        )
        ProductVariant.objects.create(
            cloth=cloth,
            size="M",
            color="Blue",
            color_code="#3b82f6",
            extra_price=Decimal("50.00"),
            stock=6,
        )
        ProductVariant.objects.create(
            cloth=cloth,
            size="L",
            color="Black",
            color_code="#111827",
            extra_price=Decimal("100.00"),
            stock=4,
        )

offer = Offers.objects.first()
if offer:
    apply_defaults(offer)

arrival = NewArrivals.objects.first()
if arrival:
    apply_defaults(arrival)

toy = Toy.objects.first()
if toy:
    apply_defaults(toy)

print(
    "seeded",
    cloth.id if cloth else None,
    offer.id if offer else None,
    arrival.id if arrival else None,
    toy.id if toy else None,
)
