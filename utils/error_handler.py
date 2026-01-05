"""
Production-ready Error Handler
Better error messages with solutions
"""

from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handles errors and provides user-friendly messages"""
    
    ERROR_MESSAGES = {
        "OutOfMemoryError": {
            "message": "❌ **VRAM Yetersiz**",
            "solutions": [
                "Resolution'ı düşür (1024 → 768)",
                "Steps sayısını azalt (8 → 6)",
                "Batch size'ı kontrol et (1 olmalı)",
                "Diğer uygulamaları kapat"
            ],
            "technical": "GPU memory insufficient for requested operation"
        },
        "TimeoutError": {
            "message": "⏱️ **Generation Timeout**",
            "solutions": [
                "Steps sayısını azalt",
                "Resolution'ı düşür",
                "Tekrar deneyin",
                "Queue'da bekleyen işlem sayısını kontrol edin"
            ],
            "technical": "Generation exceeded maximum time limit"
        },
        "RateLimitError": {
            "message": "🚫 **Rate Limit Aşıldı**",
            "solutions": [
                f"Biraz bekleyin ({'{time}'} saniye)",
                "Premium üyelik alın (daha yüksek limit)",
                "Daha az sıklıkla istek gönderin"
            ],
            "technical": "Too many requests in time window"
        },
        "InvalidPromptError": {
            "message": "⚠️ **Geçersiz Prompt**",
            "solutions": [
                "Prompt'unuzu kontrol edin",
                "Çok uzun prompt'lar kullanmayın",
                "Özel karakterlerden kaçının"
            ],
            "technical": "Prompt validation failed"
        },
        "ModelNotFoundError": {
            "message": "❌ **Model Bulunamadı**",
            "solutions": [
                "Model dosyalarını kontrol edin",
                "SETUP.md dosyasına bakın",
                "Model path'lerini kontrol edin"
            ],
            "technical": "Required model file not found"
        },
        "ComfyUIError": {
            "message": "🔌 **ComfyUI Bağlantı Hatası**",
            "solutions": [
                "ComfyUI'nin çalıştığından emin olun",
                "Port 8188'in açık olduğunu kontrol edin",
                "ComfyUI log'larını kontrol edin"
            ],
            "technical": "ComfyUI server connection failed"
        },
        "QueueFullError": {
            "message": "📋 **Queue Dolu**",
            "solutions": [
                "Biraz bekleyin",
                "Queue'daki işlemlerin bitmesini bekleyin",
                "Premium üyelik alın (öncelik)"
            ],
            "technical": "Generation queue is full"
        },
        "InsufficientCreditsError": {
            "message": "💰 **Yetersiz Kredi**",
            "solutions": [
                "Kredi bakiyenizi kontrol edin: `/credits`",
                "Kredi satın alın",
                "Premium üyelik alın (sınırsız)"
            ],
            "technical": "User does not have enough credits"
        },
        "InvalidParametersError": {
            "message": "⚠️ **Geçersiz Parametreler**",
            "solutions": [
                "Parametreleri kontrol edin",
                "Min/max değerlere dikkat edin",
                "Help komutuna bakın: `/help`"
            ],
            "technical": "Invalid generation parameters"
        }
    }
    
    @staticmethod
    def get_error_message(error_type: str, context: Optional[Dict] = None) -> str:
        """Get user-friendly error message"""
        error_info = ErrorHandler.ERROR_MESSAGES.get(error_type, {
            "message": "❌ **Bir Hata Oluştu**",
            "solutions": ["Tekrar deneyin", "Sorun devam ederse destek alın"],
            "technical": str(error_type)
        })
        
        message = error_info["message"]
        
        if error_info.get("solutions"):
            message += "\n\n**Çözüm Önerileri:**\n"
            for i, solution in enumerate(error_info["solutions"], 1):
                # Replace placeholders
                solution_text = solution
                if context:
                    if "{time}" in solution_text:
                        solution_text = solution_text.replace("{time}", str(context.get("reset_in", "?")))
                
                message += f"{i}. {solution_text}\n"
        
        # Add technical info in debug mode
        if context and context.get("debug", False):
            message += f"\n*Teknik Detay: {error_info['technical']}*"
        
        return message
    
    @staticmethod
    def handle_exception(e: Exception, context: Optional[Dict] = None) -> str:
        """Handle exception and return user-friendly message"""
        error_type = type(e).__name__
        
        # Map common exceptions
        if "memory" in str(e).lower() or "cuda" in str(e).lower():
            error_type = "OutOfMemoryError"
        elif "timeout" in str(e).lower():
            error_type = "TimeoutError"
        elif "rate limit" in str(e).lower():
            error_type = "RateLimitError"
        elif "not found" in str(e).lower():
            error_type = "ModelNotFoundError"
        elif "connection" in str(e).lower():
            error_type = "ComfyUIError"
        
        logger.error(f"Error: {error_type} - {str(e)}", exc_info=True)
        
        return ErrorHandler.get_error_message(error_type, context)

