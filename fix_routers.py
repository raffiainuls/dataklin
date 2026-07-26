with open("backend/app/routers/rules.py", "r") as f:
    content = f.read()

new_code = """
class DedupRule(BaseModel):
    column: str
    method: str
    weight: float

class DedupConfigUpdate(BaseModel):
    threshold: float
    rules: list[DedupRule]

@router.get("/datasets/{dataset_id}/dedup-config")
def get_dedup_config(dataset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dataset = _get_dataset(dataset_id, db, user)
    return dataset.dedup_config or {}

@router.put("/datasets/{dataset_id}/dedup-config")
def update_dedup_config(dataset_id: int, body: DedupConfigUpdate, db: Session = Depends(get_db), user: User = Depends(require_writer)):
    dataset = _get_dataset(dataset_id, db, user)
    
    total_weight = sum(r.weight for r in body.rules)
    if body.rules and abs(total_weight - 100.0) > 0.01:
        raise HTTPException(400, "Total bobot rule deduplikasi harus tepat 100%")
        
    dataset.dedup_config = body.model_dump()
    db.commit()
    
    # Trigger ulang kalkulasi cluster karena rule deduplikasi berubah
    enqueue_refresh_dataset(dataset.id, db)
    return dataset.dedup_config

"""

# Insert before router = APIRouter(tags=["rules"]) or at the end
content += new_code
with open("backend/app/routers/rules.py", "w") as f:
    f.write(content)
