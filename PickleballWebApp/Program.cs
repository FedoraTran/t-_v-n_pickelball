using Supabase;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorPages();
builder.Services.AddAuthentication("CookieAuth")
    .AddCookie("CookieAuth", options =>
    {
        options.Cookie.Name = "CookieAuth";
        options.LoginPath = "/Login";
    });

// ━━━ THÊM SUPABASE CLIENT ━━━
var supabaseUrl     = builder.Configuration["Supabase:Url"]
    ?? throw new Exception("Supabase:Url chưa được cấu hình");
var supabaseAnonKey = builder.Configuration["Supabase:AnonKey"]
    ?? throw new Exception("Supabase:AnonKey chưa được cấu hình");

builder.Services.AddScoped<Supabase.Client>(_ =>
{
    var options = new Supabase.SupabaseOptions
    {
        AutoConnectRealtime = false,  // không cần realtime
        AutoRefreshToken    = true
    };
    var client = new Supabase.Client(supabaseUrl, supabaseAnonKey, options);
    client.InitializeAsync().GetAwaiter().GetResult();
    return client;
});

// Service cũ vẫn giữ tạm để chưa break các page khác
builder.Services.AddScoped<PickleballWebApp.Services.UserDataService>();

// ━━━ THÊM SERVICE MỚI ━━━
builder.Services.AddScoped<PickleballWebApp.Services.SupabaseUserDataService>();

var app = builder.Build();

// (phần còn lại giữ nguyên)
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseRouting();
app.UseAuthentication();
app.UseAuthorization();
app.UseMiddleware<PickleballWebApp.Middleware.PageTrackingMiddleware>();
app.MapRazorPages();
app.Run();
