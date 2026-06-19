using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Supabase.Gotrue;

namespace PickleballWebApp.Pages
{
    public class RegisterModel : PageModel
    {
        private readonly Supabase.Client _supabase;

        public RegisterModel(Supabase.Client supabase)
        {
            _supabase = supabase;
        }

        [BindProperty] public string Email       { get; set; } = "";
        [BindProperty] public string Password    { get; set; } = "";
        [BindProperty] public string DisplayName { get; set; } = "";

        public void OnGet() { }

        public async Task<IActionResult> OnPostAsync()
        {
            if (string.IsNullOrWhiteSpace(Email) || Password.Length < 6)
            {
                ModelState.AddModelError("", "Email và mật khẩu (≥6 ký tự) là bắt buộc.");
                return Page();
            }

            try
            {
                var options = new SignUpOptions
                {
                    Data = new Dictionary<string, object>
                    {
                        ["display_name"] = DisplayName,
                        ["username"]     = Email.Split('@')[0]
                    }
                };

                var session = await _supabase.Auth.SignUp(Email, Password, options);

                if (session?.User == null)
                {
                    ModelState.AddModelError("", "Đăng ký thất bại.");
                    return Page();
                }

                // Tùy chính sách: tự động đăng nhập hay yêu cầu verify email trước
                TempData["Message"] = "Đăng ký thành công! Hãy kiểm tra email để xác nhận.";
                return RedirectToPage("/Login");
            }
            catch (Exception ex)
            {
                ModelState.AddModelError("", $"Lỗi: {ex.Message}");
                return Page();
            }
        }
    }
}
