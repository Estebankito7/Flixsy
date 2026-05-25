from django.db import models


class Item(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="título")
    descripcion = models.TextField(verbose_name="descripción")
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name="fecha de creación"
    )

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "ítem"
        verbose_name_plural = "ítems"

    def __str__(self) -> str:
        return self.titulo

    def __repr__(self) -> str:
        return f"<Item(pk={self.pk}, titulo={self.titulo!r})>"
