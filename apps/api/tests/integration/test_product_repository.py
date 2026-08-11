from app.adapters.db.repositories import ProductRepository
from app.domain.products.entities import ProductSnapshot


async def test_product_repository_appends_snapshot_without_overwriting_previous(
    product_repository: ProductRepository,
    sample_snapshot: ProductSnapshot,
) -> None:
    first = await product_repository.add_snapshot(sample_snapshot)
    second = await product_repository.add_snapshot(
        ProductSnapshot.create(
            source_id=sample_snapshot.source_id,
            title="Pulse Mix Updated",
            description=sample_snapshot.description,
            category_path=sample_snapshot.category_path,
            images=sample_snapshot.images,
            price_amount=sample_snapshot.price_amount,
            price_currency=sample_snapshot.price_currency,
        )
    )

    stored = await product_repository.list_snapshots(sample_snapshot.source_id)

    assert [item.id for item in stored] == [first.id, second.id]
    assert stored[0].title == "Pulse Mix"
