import bleach
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.news import News, Comment
from app.schemas.news import NewsResponse, NewsCreate, NewsUpdate, CommentResponse, CommentCreate
from app.api.deps import PermissionChecker, get_current_active_user
from app.services.audit_service import audit_service
from app.models.user import User

router = APIRouter()

def sanitize_html(text: str) -> str:
    """Sanitiza texto HTML para mitigar vectores de ataque XSS usando Bleach."""
    if not text:
        return ""
    # Permitir solo algunas etiquetas seguras básicas
    allowed_tags = ["p", "b", "i", "u", "strong", "em", "h1", "h2", "h3", "ul", "ol", "li", "br"]
    return bleach.clean(text, tags=allowed_tags, strip=True)


@router.get("", response_model=List[NewsResponse])
def get_news(
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtiene el boletín de noticias corporativas, ordenado por fecha."""
    query = db.query(News)
    if category:
        query = query.filter(News.category == category)
    if featured is not None:
        query = query.filter(News.is_featured == featured)
        
    return query.order_by(News.is_featured.desc(), News.created_at.desc()).all()


@router.post("", response_model=NewsResponse, status_code=status.HTTP_201_CREATED)
def create_news(
    request: Request,
    news_data: NewsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("news:manage"))
):
    """Publica un nuevo artículo o boletín de noticias corporativas (Sanitizado contra XSS)."""
    sanitized_content = sanitize_html(news_data.content)
    sanitized_title = bleach.clean(news_data.title, strip=True)
    
    db_news = News(
        title=sanitized_title,
        content=sanitized_content,
        category=news_data.category,
        is_featured=news_data.is_featured,
        author_id=current_user.id
    )
    db.add(db_news)
    db.commit()
    db.refresh(db_news)

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="news_create",
        ip_address=request.client.host if request.client else None,
        details=f"Publicó la noticia '{db_news.title}' (Categoría: {db_news.category}, Destacada: {db_news.is_featured})"
    )

    return db_news


@router.put("/{news_id}", response_model=NewsResponse)
def update_news(
    news_id: int,
    request: Request,
    news_data: NewsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("news:manage"))
):
    """Modifica un artículo de noticias existente."""
    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")

    if news_data.title:
        db_news.title = bleach.clean(news_data.title, strip=True)
    if news_data.content:
        db_news.content = sanitize_html(news_data.content)
    if news_data.category:
        db_news.category = news_data.category
    if news_data.is_featured is not None:
        db_news.is_featured = news_data.is_featured

    db.commit()
    db.refresh(db_news)

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="news_update",
        ip_address=request.client.host if request.client else None,
        details=f"Actualizó la noticia ID {db_news.id} ('{db_news.title}')"
    )

    return db_news


@router.delete("/{news_id}")
def delete_news(
    news_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker("news:manage"))
):
    """Elimina una publicación de noticias de la plataforma."""
    db_news = db.query(News).filter(News.id == news_id).first()
    if not db_news:
        raise HTTPException(status_code=404, detail="Artículo no encontrado.")

    title = db_news.title
    db.delete(db_news)
    db.commit()

    # Auditoría
    audit_service.log_action(
        db=db,
        user_id=current_user.id,
        action="news_delete",
        ip_address=request.client.host if request.client else None,
        details=f"Eliminó el artículo de noticias '{title}'."
    )

    return {"detail": "Publicación eliminada correctamente."}


# --- COMENTARIOS ---

@router.post("/{news_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    news_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Añade un comentario a un artículo corporativo (Sanitizado contra XSS)."""
    # Verificar si existe la noticia
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="Artículo de noticia no existe.")

    # Sanitización estricta contra XSS
    sanitized_content = bleach.clean(comment_data.content, strip=True)

    db_comment = Comment(
        content=sanitized_content,
        news_id=news_id,
        author_id=current_user.id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return db_comment


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Permite eliminar un comentario al autor, al administrador o al creador de la noticia."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comentario no encontrado.")

    # Autoridad para borrar: creador del comentario, administrador o autor de la noticia original
    can_delete = (
        current_user.role.name == "Administrador" or
        comment.author_id == current_user.id or
        comment.news.author_id == current_user.id
    )

    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No posee los permisos para eliminar este comentario."
        )

    db.delete(comment)
    db.commit()
    return {"detail": "Comentario eliminado correctamente."}
