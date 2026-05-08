module.exports = {
  apps: [
    {
      name: 'evacare-api',
      cwd: '/var/www/evacare/backend',
      script: '.venv/bin/python',
      args: '-m uvicorn main:app --host 127.0.0.1 --port 8623',
      interpreter: 'none',
      env: {
        PYTHONUNBUFFERED: '1',
        ENVIRONMENT: 'production',
      },
    },
  ],
}
