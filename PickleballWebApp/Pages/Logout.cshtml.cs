using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace PickleballWebApp.Pages
{
    public class LogoutModel : PageModel
    {
        private readonly Supabase.Client _supabase;

        public LogoutModel(Supabase.Client supabase)
        {
            _supabase = supabase;
        }

        public async Task<IActionResult> OnGetAsync()
        {
            await _supabase.Auth.SignOut();
            await HttpContext.SignOutAsync("CookieAuth");
            return RedirectToPage("/Index");
        }
    }
}
