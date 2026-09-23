from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import context

router = APIRouter(prefix="/api/v1", tags=["operators"])


@router.get("/operators")
def list_operators(db: Session = Depends(get_db)):
    operators = context.list_operators(db)
    return [
        {
            **context.serialize_operator(op),
            "machine": context.serialize_machine(context.get_machine_for_operator(db, op.id)),
        }
        for op in operators
    ]


@router.get("/operators/{operator_id}")
def get_operator(operator_id: str, db: Session = Depends(get_db)):
    operator = context.get_operator(db, operator_id)
    if operator is None:
        raise HTTPException(status_code=404, detail=f"Unknown operator {operator_id}")
    return {
        **context.serialize_operator(operator),
        "machine": context.serialize_machine(context.get_machine_for_operator(db, operator_id)),
    }
