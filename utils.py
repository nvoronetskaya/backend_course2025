from model.item import Item

async def load_synthetic_data(repository):
        items = [
            Item(
                name="Wireless Earbuds X2",
                description="Compact TWS earbuds with active noise reduction and 20h total playback.",
                category=2,
                images_qty=5,
            ),
            Item(
                name="Smartwatch Pulse Pro",
                description="Fitness-oriented smartwatch with heart-rate tracking, GPS, and sleep analytics.",
                category=2,
                images_qty=4,
            ),
            Item(
                name="Mechanical Keyboard K87",
                description="Tenkeyless mechanical keyboard with hot-swappable switches and RGB backlight.",
                category=2,
                images_qty=6,
            ),
            Item(
                name="Coffee Grinder Mini",
                description="Burr grinder for consistent grind size; suitable for espresso and pour-over.",
                category=3,
                images_qty=3,
            ),
            Item(
                name="Stainless Water Bottle 1L",
                description="Vacuum insulated bottle keeps drinks cold up to 24h and hot up to 12h.",
                category=3,
                images_qty=2,
            ),
            Item(
                name="Yoga Mat Grip 6mm",
                description="Non-slip yoga mat with dense cushioning; easy to clean surface.",
                category=4,
                images_qty=4,
            ),
            Item(
                name="Dumbbells Set 2x10kg",
                description="Adjustable dumbbell set with anti-slip grip and protective floor plates.",
                category=4,
                images_qty=5,
            ),
            Item(
                name="LED Desk Lamp Aurora",
                description="Dimmable desk lamp with warm/cool modes and USB charging port.",
                category=5,
                images_qty=3,
            ),
            Item(
                name="Backpack Urban 25L",
                description="Water-resistant city backpack with laptop compartment and hidden pocket.",
                category=6,
                images_qty=6,
            ),
            Item(
                name="Winter Jacket Arctic Shell",
                description="Lightweight insulated jacket with windproof outer layer and deep hood.",
                category=7,
                images_qty=7,
            )
        ]
        for item in items:
            await repository.create_item(item)
