"""
Sistema de validación y detección de violaciones para el apilado de cajas.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from .box import Box


class ViolationType(Enum):
    """Tipos de violaciones de condiciones de apilado."""
    INSUFFICIENT_SUPPORT_AREA = "insufficient_support_area"
    INSUFFICIENT_SUPPORT_WEIGHT = "insufficient_support_weight"
    EXCESSIVE_HEIGHT = "excessive_height"
    UNSTABLE_PLACEMENT = "unstable_placement"
    WEIGHT_OVERLOAD = "weight_overload"
    DIMENSION_EXCEEDED = "dimension_exceeded"


@dataclass
class StackingViolation:
    """Representa una violación de condiciones de apilado."""
    violation_type: ViolationType
    box_id: str
    message: str
    severity: str  # "warning", "error", "critical"
    current_value: float
    limit_value: float
    recommendation: str


@dataclass
class StackingConfig:
    """Configuración de límites para el apilado de cajas."""
    # Límites de estabilidad (relajados)
    min_support_area_ratio: float = 0.25  # Era 0.75, ahora 0.25 (más permisivo)
    min_support_weight_ratio: float = 0.3  # Era 0.5, ahora 0.3 (más permisivo)
    
    # Límites de altura
    max_height_multiplier: float = 1.2  # Permitir 20% más altura
    
    # Límites de peso
    max_weight_multiplier: float = 1.1  # Permitir 10% más peso
    
    # Configuración de warnings
    show_warnings: bool = True
    allow_violations: bool = True  # Permitir colocación aunque haya violaciones
    
    # Umbrales de severidad
    warning_threshold: float = 0.5  # Por debajo de esto es warning
    error_threshold: float = 0.25   # Por debajo de esto es error
    critical_threshold: float = 0.1 # Por debajo de esto es crítico


class StackingValidator:
    """Validador de condiciones de apilado con detección de violaciones."""
    
    def __init__(self, config: StackingConfig = None):
        self.config = config or StackingConfig()
        self.violations: List[StackingViolation] = []
        self.stats = {
            "total_checks": 0,
            "violations_detected": 0,
            "warnings": 0,
            "errors": 0,
            "critical": 0
        }
    
    def validate_stacking(self, box: Box, pallet: Any, position: Tuple[float, float, float]) -> Tuple[bool, List[StackingViolation]]:
        """
        Valida si una caja puede ser apilada en una posición específica.
        
        Args:
            box: Caja a colocar
            position: Posición (x, y, z) donde colocar la caja
            pallet: Pallet donde se coloca la caja
            
        Returns:
            Tuple[bool, List[StackingViolation]]: (puede_colocarse, lista_de_violaciones)
        """
        self.stats["total_checks"] += 1
        violations = []
        
        x, y, z = position
        
        # Si está en el suelo (z=0), no hay violaciones de apilado
        if z == 0:
            return True, violations
        
        # 1. Verificar área de soporte
        support_violations = self._check_support_area(box, pallet, position)
        violations.extend(support_violations)
        
        # 2. Verificar peso de soporte
        weight_violations = self._check_support_weight(box, pallet, position)
        violations.extend(weight_violations)
        
        # 3. Verificar altura máxima
        height_violations = self._check_height_limits(box, pallet, position)
        violations.extend(height_violations)
        
        # 4. Verificar límites de peso del pallet
        weight_limit_violations = self._check_weight_limits(box, pallet)
        violations.extend(weight_limit_violations)
        
        # 5. Verificar dimensiones del pallet
        dimension_violations = self._check_dimension_limits(box, pallet, position)
        violations.extend(dimension_violations)
        
        # Actualizar estadísticas
        self._update_stats(violations)
        
        # Determinar si se puede colocar
        can_place = self._determine_placement(violations)
        
        return can_place, violations
    
    def _check_support_area(self, box: Box, pallet: Any, position: Tuple[float, float, float]) -> List[StackingViolation]:
        """Verifica el área de soporte para la caja."""
        violations = []
        x, y, z = position
        
        # Calcular área de la caja
        box_area = box.get_effective_width() * box.get_effective_length()
        
        # Encontrar cajas de soporte
        support_area = 0
        supporting_boxes = []
        
        for other_box in pallet.boxes:
            if (hasattr(other_box, 'position') and 
                other_box.position and 
                len(other_box.position) >= 3 and
                other_box.position[2] + other_box.get_effective_height() == z):
                
                # Calcular intersección
                overlap_x = min(x + box.get_effective_width(), 
                              other_box.position[0] + other_box.get_effective_width()) - \
                           max(x, other_box.position[0])
                overlap_y = min(y + box.get_effective_length(), 
                              other_box.position[1] + other_box.get_effective_length()) - \
                           max(y, other_box.position[1])
                
                if overlap_x > 0 and overlap_y > 0:
                    support_area += overlap_x * overlap_y
                    supporting_boxes.append(other_box)
        
        # Calcular ratio de soporte
        support_ratio = support_area / box_area if box_area > 0 else 0
        
        # Verificar si cumple el límite mínimo
        if support_ratio < self.config.min_support_area_ratio:
            severity = self._get_severity(support_ratio, self.config.min_support_area_ratio)
            
            violation = StackingViolation(
                violation_type=ViolationType.INSUFFICIENT_SUPPORT_AREA,
                box_id=str(box.id),
                message=f"Área de soporte insuficiente: {support_ratio:.2%} (mínimo: {self.config.min_support_area_ratio:.2%})",
                severity=severity,
                current_value=support_ratio,
                limit_value=self.config.min_support_area_ratio,
                recommendation=f"Necesita al menos {self.config.min_support_area_ratio:.2%} de área de soporte. Cajas de soporte: {len(supporting_boxes)}"
            )
            violations.append(violation)
        
        return violations
    
    def _check_support_weight(self, box: Box, pallet: Any, position: Tuple[float, float, float]) -> List[StackingViolation]:
        """Verifica el peso de soporte para la caja."""
        violations = []
        x, y, z = position
        
        # Calcular peso total de soporte
        total_support_weight = 0
        supporting_boxes = []
        
        for other_box in pallet.boxes:
            if (hasattr(other_box, 'position') and 
                other_box.position and 
                len(other_box.position) >= 3 and
                other_box.position[2] + other_box.get_effective_height() == z):
                
                # Verificar si hay intersección
                overlap_x = min(x + box.get_effective_width(), 
                              other_box.position[0] + other_box.get_effective_width()) - \
                           max(x, other_box.position[0])
                overlap_y = min(y + box.get_effective_length(), 
                              other_box.position[1] + other_box.get_effective_length()) - \
                           max(y, other_box.position[1])
                
                if overlap_x > 0 and overlap_y > 0:
                    total_support_weight += other_box.weight
                    supporting_boxes.append(other_box)
        
        # Calcular ratio de peso de soporte
        support_weight_ratio = total_support_weight / box.weight if box.weight > 0 else 0
        
        # Verificar si cumple el límite mínimo
        if support_weight_ratio < self.config.min_support_weight_ratio:
            severity = self._get_severity(support_weight_ratio, self.config.min_support_weight_ratio)
            
            violation = StackingViolation(
                violation_type=ViolationType.INSUFFICIENT_SUPPORT_WEIGHT,
                box_id=str(box.id),
                message=f"Peso de soporte insuficiente: {support_weight_ratio:.2%} (mínimo: {self.config.min_support_weight_ratio:.2%})",
                severity=severity,
                current_value=support_weight_ratio,
                limit_value=self.config.min_support_weight_ratio,
                recommendation=f"Necesita al menos {self.config.min_support_weight_ratio:.2%} del peso como soporte. Peso de soporte: {total_support_weight:.2f} kg"
            )
            violations.append(violation)
        
        return violations
    
    def _check_height_limits(self, box: Box, pallet: Any, position: Tuple[float, float, float]) -> List[StackingViolation]:
        """Verifica los límites de altura."""
        violations = []
        x, y, z = position
        
        # Calcular altura máxima permitida
        max_allowed_height = pallet.max_height * self.config.max_height_multiplier
        
        # Calcular altura actual de la caja
        current_height = z + box.get_effective_height()
        
        if current_height > max_allowed_height:
            severity = "error" if current_height > pallet.max_height else "warning"
            
            violation = StackingViolation(
                violation_type=ViolationType.EXCESSIVE_HEIGHT,
                box_id=str(box.id),
                message=f"Altura excesiva: {current_height:.1f} cm (máximo: {max_allowed_height:.1f} cm)",
                severity=severity,
                current_value=current_height,
                limit_value=max_allowed_height,
                recommendation=f"Reducir altura o usar pallet más alto. Altura actual: {current_height:.1f} cm"
            )
            violations.append(violation)
        
        return violations
    
    def _check_weight_limits(self, box: Box, pallet: Any) -> List[StackingViolation]:
        """Verifica los límites de peso del pallet."""
        violations = []
        
        # Calcular peso máximo permitido
        max_allowed_weight = pallet.max_weight * self.config.max_weight_multiplier
        
        # Calcular peso total con la nueva caja
        total_weight = pallet.current_weight + box.weight
        
        if total_weight > max_allowed_weight:
            severity = "error" if total_weight > pallet.max_weight else "warning"
            
            violation = StackingViolation(
                violation_type=ViolationType.WEIGHT_OVERLOAD,
                box_id=str(box.id),
                message=f"Sobrecarga de peso: {total_weight:.1f} kg (máximo: {max_allowed_weight:.1f} kg)",
                severity=severity,
                current_value=total_weight,
                limit_value=max_allowed_weight,
                recommendation=f"Usar pallet con mayor capacidad de peso. Peso actual: {total_weight:.1f} kg"
            )
            violations.append(violation)
        
        return violations
    
    def _check_dimension_limits(self, box: Box, pallet: Any, position: Tuple[float, float, float]) -> List[StackingViolation]:
        """Verifica los límites de dimensiones del pallet."""
        violations = []
        x, y, z = position
        
        # Verificar límites de ancho y largo
        if (x + box.get_effective_width() > pallet.max_width or
            y + box.get_effective_length() > pallet.max_length):
            
            violation = StackingViolation(
                violation_type=ViolationType.DIMENSION_EXCEEDED,
                box_id=str(box.id),
                message=f"Dimensiones excedidas: {box.get_effective_width()}x{box.get_effective_length()} cm (máximo: {pallet.max_width}x{pallet.max_length} cm)",
                severity="error",
                current_value=max(x + box.get_effective_width() - pallet.max_width, 
                                y + box.get_effective_length() - pallet.max_length),
                limit_value=0,
                recommendation=f"Usar pallet más grande o rotar la caja. Dimensiones: {box.get_effective_width()}x{box.get_effective_length()} cm"
            )
            violations.append(violation)
        
        return violations
    
    def _get_severity(self, current_value: float, limit_value: float) -> str:
        """Determina la severidad de una violación."""
        ratio = current_value / limit_value if limit_value > 0 else 0
        
        if ratio >= self.config.warning_threshold:
            return "warning"
        elif ratio >= self.config.error_threshold:
            return "error"
        else:
            return "critical"
    
    def _update_stats(self, violations: List[StackingViolation]):
        """Actualiza las estadísticas de violaciones."""
        self.stats["violations_detected"] += len(violations)
        
        for violation in violations:
            if violation.severity == "warning":
                self.stats["warnings"] += 1
            elif violation.severity == "error":
                self.stats["errors"] += 1
            elif violation.severity == "critical":
                self.stats["critical"] += 1
    
    def _determine_placement(self, violations: List[StackingViolation]) -> bool:
        """Determina si se puede colocar la caja a pesar de las violaciones."""
        if not self.config.allow_violations:
            return len(violations) == 0
        
        # Permitir colocación si solo hay warnings
        critical_violations = [v for v in violations if v.severity == "critical"]
        error_violations = [v for v in violations if v.severity == "error"]
        
        # No permitir si hay violaciones críticas
        if critical_violations:
            return False
        
        # Permitir errores solo si está configurado
        if error_violations and not self.config.allow_violations:
            return False
        
        return True
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen de las violaciones detectadas."""
        return {
            "total_checks": self.stats["total_checks"],
            "violations_detected": self.stats["violations_detected"],
            "violation_rate": self.stats["violations_detected"] / max(self.stats["total_checks"], 1),
            "warnings": self.stats["warnings"],
            "errors": self.stats["errors"],
            "critical": self.stats["critical"],
            "config": {
                "min_support_area_ratio": self.config.min_support_area_ratio,
                "min_support_weight_ratio": self.config.min_support_weight_ratio,
                "max_height_multiplier": self.config.max_height_multiplier,
                "max_weight_multiplier": self.config.max_weight_multiplier,
                "allow_violations": self.config.allow_violations
            }
        }
    
    def clear_violations(self):
        """Limpia la lista de violaciones."""
        self.violations.clear()
        self.stats = {
            "total_checks": 0,
            "violations_detected": 0,
            "warnings": 0,
            "errors": 0,
            "critical": 0
        }
