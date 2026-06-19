using System;
using System.Security.Claims;

namespace PickleballWebApp.Extensions
{
    public static class ClaimsPrincipalExtensions
    {
        public static Guid GetSupabaseUserId(this ClaimsPrincipal user)
        {
            var idClaim = user.FindFirst(ClaimTypes.NameIdentifier)?.Value;
            return Guid.TryParse(idClaim, out var id) ? id : Guid.Empty;
        }
    }
}
